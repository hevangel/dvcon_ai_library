import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ChatPanel } from './chat_panel'

function render_panel(overrides: Partial<Parameters<typeof ChatPanel>[0]> = {}) {
    const on_submit = vi.fn().mockResolvedValue(undefined)
    const base = {
        messages: [],
        citations: [],
        show_help: true,
        is_loading: false,
        selected_papers: [],
        on_submit,
    }
    render(<ChatPanel {...base} {...overrides} />)
    return { on_submit }
}

function get_input(): HTMLTextAreaElement {
    return screen.getByPlaceholderText(/Ask a question about the selected papers/i) as HTMLTextAreaElement
}

describe('ChatPanel', () => {
    it('Enter submits the drafted message', async () => {
        const { on_submit } = render_panel()
        const input = get_input()
        fireEvent.change(input, { target: { value: 'Summarize the paper' } })
        fireEvent.keyDown(input, { key: 'Enter', shiftKey: false })

        await Promise.resolve()
        expect(on_submit).toHaveBeenCalledTimes(1)
        expect(on_submit).toHaveBeenCalledWith('Summarize the paper')
    })

    it('Shift+Enter does not submit (inserts a newline instead)', () => {
        const { on_submit } = render_panel()
        const input = get_input()
        fireEvent.change(input, { target: { value: 'Two\nlines' } })
        fireEvent.keyDown(input, { key: 'Enter', shiftKey: true })
        expect(on_submit).not.toHaveBeenCalled()
    })

    it('does not submit an empty draft', () => {
        const { on_submit } = render_panel()
        fireEvent.keyDown(get_input(), { key: 'Enter', shiftKey: false })
        expect(on_submit).not.toHaveBeenCalled()
    })

    it('Submit button sends the drafted message', async () => {
        const { on_submit } = render_panel()
        fireEvent.change(get_input(), { target: { value: 'hello' } })
        fireEvent.click(screen.getByRole('button', { name: /submit/i }))
        await Promise.resolve()
        expect(on_submit).toHaveBeenCalledWith('hello')
    })

    it('shows the help panel when show_help is true', () => {
        render_panel({ show_help: true })
        expect(screen.getByRole('heading', { level: 6, name: 'Chat commands' })).toBeInTheDocument()
    })
})
