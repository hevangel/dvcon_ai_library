import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { SearchResultsTab } from './search_results_tab'
import type { SearchResultItem } from '../types/api'

const sample_results: SearchResultItem[] = [
    {
        paper_id: 1,
        title: 'First Sample Paper',
        abstract: 'Abstract one.',
        authors: ['Alice Example'],
        affiliations: ['Example Semiconductor'],
        year: 2024,
        location: 'united states',
        conference_name: 'DVCon United States 2024',
        score: 0.9,
        snippet: 'A snippet.',
    },
    {
        paper_id: 2,
        title: 'Second Sample Paper',
        abstract: 'Abstract two.',
        authors: ['Bob Verifier'],
        affiliations: ['Verification Labs'],
        year: 2025,
        location: 'india',
        conference_name: 'DVCon India 2025',
        score: 0.7,
        snippet: 'Another snippet.',
    },
]

function render_tab(overrides: Partial<Parameters<typeof SearchResultsTab>[0]> = {}) {
    const on_toggle_paper = vi.fn()
    const on_activate_paper = vi.fn()
    const on_search = vi.fn()
    const base = {
        loading: false,
        results: sample_results,
        active_paper_id: null,
        selected_paper_ids: [],
        initial_query: '',
        initial_mode: 'hybrid' as const,
        on_search,
        on_toggle_paper,
        on_activate_paper,
    }
    const { rerender } = render(<SearchResultsTab {...base} {...overrides} />)
    return { on_toggle_paper, on_activate_paper, on_search, rerender }
}

describe('SearchResultsTab', () => {
    it('renders every result title', () => {
        render_tab()
        expect(screen.getByText('First Sample Paper')).toBeInTheDocument()
        expect(screen.getByText('Second Sample Paper')).toBeInTheDocument()
    })

    it('clicking a result row activates that paper', () => {
        const { on_activate_paper } = render_tab()
        fireEvent.click(screen.getByText('Second Sample Paper'))
        expect(on_activate_paper).toHaveBeenCalledWith(2)
    })

    it('clicking a checkbox toggles selection without activating', () => {
        const { on_toggle_paper, on_activate_paper } = render_tab()
        const checkboxes = screen.getAllByRole('checkbox')
        fireEvent.click(checkboxes[1])
        expect(on_toggle_paper).toHaveBeenCalledWith(2)
        expect(on_activate_paper).not.toHaveBeenCalled()
    })

    it('shows the empty state when there are no results and not loading', () => {
        render_tab({ results: [] })
        expect(screen.getByText(/No papers matched the current search criteria/i)).toBeInTheDocument()
    })
})
