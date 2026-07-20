import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Unmount rendered components between tests so a previous test's DOM doesn't
// leak into the next (e.g. duplicate "Chat commands" headings).
afterEach(() => {
    cleanup()
})

// jsdom does not implement scrollIntoView; chat_panel.tsx auto-scrolls to the
// newest message on every transcript change via a ref.
if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => {}
}

// jsdom does not implement matchMedia; MUI's useMediaQuery (used in App.tsx)
// calls it at render time and would crash without this shim.
if (!window.matchMedia) {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: (query: string) => ({
            matches: false,
            media: query,
            onchange: null,
            addEventListener: () => {},
            removeEventListener: () => {},
            addListener: () => {},
            removeListener: () => {},
            dispatchEvent: () => false,
        }),
    })
}

// jsdom does not implement ResizeObserver; pdf_tab.tsx uses one to auto-fit
// the rendered PDF page width.
class ResizeObserverStub {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
}
if (!globalThis.ResizeObserver) {
    ;(globalThis as { ResizeObserver?: unknown }).ResizeObserver = ResizeObserverStub
}
