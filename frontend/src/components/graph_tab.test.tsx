import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { GraphElementData, GraphResponse, PaperDetailResponse } from '../types/api'

// Mock react-cytoscapejs so we can capture the `cy` callback prop and
// synthesize `tap node` events. The real CytoscapeComponent drives a canvas
// imperitively via the cytoscape library, which jsdom cannot exercise.
//
// The fake component captures the `cy` init callback into `last_captured_cy`
// on each mount, and the fake `cy.on('tap', 'node', handler)` records the
// handler so tests can fire it with a controlled node payload.

type TapHandler = (event: { target: { data: () => unknown } }) => void
interface CapturedCy {
    tap_handlers: TapHandler[]
}

let last_captured_cy: CapturedCy = { tap_handlers: [] }

vi.mock('react-cytoscapejs', () => ({
    default: function FakeCytoscapeComponent(props: {
        cy?: (cy: { on: (event: string, selector: string, handler: TapHandler) => void }) => void
    }) {
        const captured: CapturedCy = { tap_handlers: [] }
        last_captured_cy = captured
        props.cy?.({
            on: (_event, _selector, handler) => {
                captured.tap_handlers.push(handler)
            },
        })
        return null
    },
}))

const { GraphTab } = await import('./graph_tab')

const paper: PaperDetailResponse = {
    paper_id: 1,
    title: 'Active Paper',
    authors: ['Jane Doe'],
    abstract: '',
    affiliations: [],
    references: [],
    year: 2025,
    location: 'india',
    conference_name: 'DVCon India 2025',
    source_url: 'https://example.com/p1',
    pdf_url: 'https://example.com/p1.pdf',
    pdf_path: 'data/paper/2025/india/p1.pdf',
}

const author_node: GraphElementData = { id: 'author-2', label: 'Jane Doe', type: 'author', author_name: 'Jane Doe' }
const company_node: GraphElementData = { id: 'company-acme', label: 'Acme Corp', type: 'company', company_name: 'Acme Corp' }
const conference_node: GraphElementData = {
    id: 'conference-3',
    label: 'DVCon India 2025',
    type: 'conference',
    conference_name: 'DVCon India 2025',
    year: 2025,
    location: 'india',
}
const resolved_reference_node: GraphElementData = {
    id: 'reference-10',
    label: 'Some Unrelated Design Paper',
    type: 'reference',
    reference_id: 10,
    paper_id: 42,
}
const unresolved_reference_node: GraphElementData = {
    id: 'reference-11',
    label: 'A Paper Not In Corpus',
    type: 'reference',
    reference_id: 11,
}

const sample_graph: GraphResponse = {
    paper_id: 1,
    nodes: [
        { data: { id: 'paper-1', label: 'Active Paper', type: 'paper', paper_id: 1 } },
        { data: author_node },
        { data: company_node },
        { data: conference_node },
        { data: resolved_reference_node },
        { data: unresolved_reference_node },
    ],
    edges: [],
}

function fire_tap(data: GraphElementData) {
    for (const handler of last_captured_cy.tap_handlers) {
        handler({ target: { data: () => data } })
    }
}

describe('GraphTab click wiring', () => {
    it('registers a tap handler on mount when on_node_click is provided', () => {
        render(<GraphTab paper={paper} graph={sample_graph} on_node_click={vi.fn()} />)
        expect(last_captured_cy.tap_handlers.length).toBeGreaterThanOrEqual(1)
    })

    it('fires on_node_click with the author payload when an author node is tapped', () => {
        const on_node_click = vi.fn()
        render(<GraphTab paper={paper} graph={sample_graph} on_node_click={on_node_click} />)
        fire_tap(author_node)
        expect(on_node_click).toHaveBeenCalledWith(author_node)
    })

    it('fires on_node_click with paper_id when a resolved reference node is tapped', () => {
        const on_node_click = vi.fn()
        render(<GraphTab paper={paper} graph={sample_graph} on_node_click={on_node_click} />)
        fire_tap(resolved_reference_node)
        expect(on_node_click).toHaveBeenCalledWith(resolved_reference_node)
        expect(resolved_reference_node.paper_id).toBe(42)
    })

    it('fires on_node_click with year+location when a conference node is tapped', () => {
        const on_node_click = vi.fn()
        render(<GraphTab paper={paper} graph={sample_graph} on_node_click={on_node_click} />)
        fire_tap(conference_node)
        expect(on_node_click).toHaveBeenCalledWith(conference_node)
    })

    it('fires on_node_click for an unresolved reference (frontend decides no-op)', () => {
        const on_node_click = vi.fn()
        render(<GraphTab paper={paper} graph={sample_graph} on_node_click={on_node_click} />)
        fire_tap(unresolved_reference_node)
        expect(on_node_click).toHaveBeenCalledWith(unresolved_reference_node)
        expect(unresolved_reference_node.paper_id).toBeUndefined()
    })
})
