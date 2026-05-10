import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
})

// jsdom 미구현 mock (Task 9 cascade hook 테스트가 의존)
// `'animate' in Element.prototype` narrowing 회피를 위해 Record 캐스트 사용
if (typeof Element !== 'undefined' && !('animate' in Element.prototype)) {
  ;(Element.prototype as unknown as Record<string, unknown>).animate = function () {
    return {
      cancel: () => {},
      finish: () => {},
      play: () => {},
      pause: () => {},
      onfinish: null,
      finished: Promise.resolve(),
    } as unknown as Animation
  }
}

if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList
}
