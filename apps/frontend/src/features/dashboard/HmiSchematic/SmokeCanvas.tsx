import { useEffect, useRef } from 'react'
import { VIEW_BOX } from './schematic-roles'

// 연기 발생 좌표 (SVG viewBox 기준)
// EXHAUST 박스(Vector_60): x 962~1010, y 210~391
// 윗변 위에 굴뚝(rect 968~1004, y 196~212) — 굴뚝 입구(986, 196)에서 솟음
const EMITTER_X = 986
const EMITTER_Y = 196
const EMITTER_SPREAD_X = 12
const EMITTER_SPREAD_Y = 2

// 연기 색 (수증기 흰색)
const SMOKE_R = 220
const SMOKE_G = 224
const SMOKE_B = 230

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  life: number      // 0~1, 1이 새로 생성, 0이 소멸
  lifeStep: number  // 매 프레임 감소량
  radius: number
  maxRadius: number
}

export interface SmokeCanvasProps {
  // 연기 강도 0~1 (NOx 농도 등)
  intensity: number
}

function createParticle(intensity: number): Particle {
  const angle = -Math.PI / 2 + (Math.random() - 0.5) * 0.4 // 위쪽 ±11°
  const speed = 0.6 + Math.random() * 0.8 + intensity * 0.6
  return {
    x: EMITTER_X + (Math.random() - 0.5) * EMITTER_SPREAD_X * 2,
    y: EMITTER_Y + (Math.random() - 0.5) * EMITTER_SPREAD_Y * 2,
    vx: Math.cos(angle) * speed * 0.4 + (Math.random() - 0.5) * 0.3,
    vy: Math.sin(angle) * speed,
    life: 1,
    lifeStep: 0.004 + Math.random() * 0.004,
    radius: 6 + Math.random() * 4,
    maxRadius: 18 + Math.random() * 14 + intensity * 12,
  }
}

export function SmokeCanvas({ intensity }: SmokeCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const intensityRef = useRef(intensity)
  useEffect(() => {
    intensityRef.current = intensity
  }, [intensity])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // prefers-reduced-motion 시 정지
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (mq.matches) return

    let scaleX = 1
    let scaleY = 1
    const particles: Particle[] = []
    let rafId = 0

    function resize() {
      const rect = canvas!.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      canvas!.width = rect.width * dpr
      canvas!.height = rect.height * dpr
      scaleX = (rect.width * dpr) / VIEW_BOX.width
      scaleY = (rect.height * dpr) / VIEW_BOX.height
    }

    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    resize()

    function frame() {
      const cur = intensityRef.current
      // 신규 입자 생성 빈도 (intensity 0 → 0/frame, 1 → ~3/frame)
      const spawn = cur * 3
      const spawnFloor = Math.floor(spawn)
      const spawnFrac = spawn - spawnFloor
      const spawnCount = spawnFloor + (Math.random() < spawnFrac ? 1 : 0)
      for (let i = 0; i < spawnCount; i++) particles.push(createParticle(cur))

      // 입자 업데이트 + 그리기
      ctx!.clearRect(0, 0, canvas!.width, canvas!.height)
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i]
        p.x += p.vx
        p.y += p.vy
        // 위로 갈수록 약간 가속 (열기둥 효과)
        p.vy *= 0.995
        // 옆으로 살짝 흔들림
        p.vx += (Math.random() - 0.5) * 0.05
        // 부풀기
        p.radius += (p.maxRadius - p.radius) * 0.04
        // 생명 감소
        p.life -= p.lifeStep

        if (p.life <= 0) {
          particles.splice(i, 1)
          continue
        }

        // 화면 좌표 (viewBox → canvas px)
        const cx = p.x * scaleX
        const cy = p.y * scaleY
        const cr = p.radius * scaleX
        // radial gradient: 중심 흐릿한 흰빛 → 외곽 투명. 진하기 max 0.22로 가벼움
        const alpha = p.life * cur * 0.22
        const grad = ctx!.createRadialGradient(cx, cy, 0, cx, cy, cr)
        grad.addColorStop(0, `rgba(${SMOKE_R}, ${SMOKE_G}, ${SMOKE_B}, ${alpha})`)
        grad.addColorStop(0.5, `rgba(${SMOKE_R}, ${SMOKE_G}, ${SMOKE_B}, ${alpha * 0.5})`)
        grad.addColorStop(1, `rgba(${SMOKE_R}, ${SMOKE_G}, ${SMOKE_B}, 0)`)
        ctx!.fillStyle = grad
        ctx!.beginPath()
        ctx!.arc(cx, cy, cr, 0, Math.PI * 2)
        ctx!.fill()
      }

      rafId = requestAnimationFrame(frame)
    }
    rafId = requestAnimationFrame(frame)

    return () => {
      cancelAnimationFrame(rafId)
      ro.disconnect()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    />
  )
}
