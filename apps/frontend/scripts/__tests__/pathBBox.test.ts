import { describe, it, expect } from 'vitest'
import { pathBBox, UnsupportedPathCommandError } from '../buildHmiSvg/pathBBox'

describe('pathBBox', () => {
  it('M+L 경로의 bbox 계산', () => {
    const bbox = pathBBox('M 10 20 L 50 80 L 30 100 Z')
    expect(bbox.x).toBe(10)
    expect(bbox.y).toBe(20)
    expect(bbox.width).toBe(40)
    expect(bbox.height).toBe(80)
  })

  it('H/V (수평/수직 라인) bbox 계산', () => {
    const bbox = pathBBox('M 10 10 H 100 V 50')
    expect(bbox.x).toBe(10)
    expect(bbox.y).toBe(10)
    expect(bbox.width).toBe(90)
    expect(bbox.height).toBe(40)
  })

  it('C (cubic Bezier) 제어점 포함 bbox', () => {
    // 시작 (0,0), 끝 (100,0), 제어점 (50,-50) (50,50) → bbox는 제어점 포함
    const bbox = pathBBox('M 0 0 C 50 -50 50 50 100 0')
    expect(bbox.x).toBe(0)
    expect(bbox.width).toBe(100)
    expect(bbox.y).toBe(-50)
    expect(bbox.height).toBe(100)
  })

  it('소문자 명령(상대좌표) 처리', () => {
    // M 10 10, l 20 0 → (10,10)→(30,10), l 0 30 → (30,40)
    const bbox = pathBBox('M 10 10 l 20 0 l 0 30')
    expect(bbox.x).toBe(10)
    expect(bbox.y).toBe(10)
    expect(bbox.width).toBe(20)
    expect(bbox.height).toBe(30)
  })

  it('Z (close path) 무시', () => {
    const bbox = pathBBox('M 0 0 L 10 0 L 10 10 Z')
    expect(bbox.width).toBe(10)
    expect(bbox.height).toBe(10)
  })

  it('미지원 명령(S)이 있으면 UnsupportedPathCommandError throw', () => {
    expect(() => pathBBox('M 0 0 S 10 10 20 20')).toThrow(UnsupportedPathCommandError)
  })

  it('미지원 명령(A)이 있으면 throw', () => {
    expect(() => pathBBox('M 0 0 A 10 10 0 0 1 20 20')).toThrow(UnsupportedPathCommandError)
  })

  it('미지원 명령(Q)이 있으면 throw', () => {
    expect(() => pathBBox('M 0 0 Q 10 10 20 20')).toThrow(UnsupportedPathCommandError)
  })

  it('빈 d 또는 M만 있으면 throw', () => {
    expect(() => pathBBox('')).toThrow()
    expect(() => pathBBox('M')).toThrow()
  })
})
