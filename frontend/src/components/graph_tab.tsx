import { Paper, Typography } from '@mui/material'
import type { Core } from 'cytoscape'
import CytoscapeComponent from 'react-cytoscapejs'

import type { GraphElementData, GraphResponse, PaperDetailResponse } from '../types/api'

interface GraphTabProps {
    paper?: PaperDetailResponse
    graph?: GraphResponse
    /** Called when the user clicks (taps) a graph node. */
    on_node_click?: (data: GraphElementData) => void
}

export function GraphTab({ paper, graph, on_node_click }: GraphTabProps) {
    if (!paper) {
        return (
            <Paper variant="outlined" sx={{ p: 4, height: '100%' }}>
                <Typography color="text.secondary">
                    Select a paper to explore authorship, conference, company, and reference relationships.
                </Typography>
            </Paper>
        )
    }

    if (!graph) {
        return (
            <Paper variant="outlined" sx={{ p: 4, height: '100%' }}>
                <Typography color="text.secondary">Graph data is not available for this paper yet.</Typography>
            </Paper>
        )
    }

    return (
        <Paper variant="outlined" sx={{ height: '100%', overflow: 'hidden', position: 'relative' }}>
            <Typography
                variant="caption"
                color="text.secondary"
                sx={{ position: 'absolute', top: 8, left: 12, zIndex: 5, pointerEvents: 'none' }}
            >
                Click a conference / author / company node to filter Search Results. Resolved reference
                nodes jump to that paper.
            </Typography>
            <CytoscapeComponent
                elements={[...graph.nodes, ...graph.edges]}
                style={{ width: '100%', height: '100%' }}
                layout={{ name: 'breadthfirst', directed: true, padding: 24 }}
                cy={(cy: Core) => {
                    if (!on_node_click) return
                    // `data` from cytoscape's event target is the node's `data`
                    // payload (id, label, type, click-target fields). Re-emit it
                    // so App.tsx can decide per-type behavior.
                    cy.on('tap', 'node', (event) => {
                        on_node_click(event.target.data() as GraphElementData)
                    })
                }}
                stylesheet={[
                    {
                        selector: 'node',
                        style: {
                            label: 'data(label)',
                            'background-color': '#1f4b99',
                            color: '#0f172a',
                            'text-wrap': 'wrap',
                            'text-max-width': 140,
                            'font-size': 11,
                            width: 'label',
                            height: 'label',
                            padding: '12px',
                            shape: 'round-rectangle',
                            'border-width': 0,
                        },
                    },
                    {
                        selector: 'edge',
                        style: {
                            label: 'data(label)',
                            width: 1.5,
                            'line-color': '#94a3b8',
                            'target-arrow-color': '#94a3b8',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                            'font-size': 10,
                        },
                    },
                    {
                        selector: 'node[type = "paper"]',
                        style: {
                            'background-color': '#0f766e',
                            color: '#0f172a',
                        },
                    },
                    {
                        selector: 'node[type = "author"]',
                        style: {
                            'background-color': '#cbd5e1',
                        },
                    },
                    {
                        selector: 'node[type = "company"]',
                        style: {
                            'background-color': '#fde68a',
                        },
                    },
                    {
                        selector: 'node[type = "conference"]',
                        style: {
                            'background-color': '#bfdbfe',
                        },
                    },
                    {
                        selector: 'node[type = "reference"]',
                        style: {
                            'background-color': '#fecaca',
                        },
                    },
                    // Clickable affordance: nodes carrying a click-target payload
                    // get a thicker accent border + pointer cursor. The active
                    // paper node also carries `paper_id` (for consistency) but is
                    // excluded — only resolved *reference* nodes are paper-jump
                    // targets. Author / company / conference nodes are always
                    // clickable. Order matters: this comes after the per-type
                    // selectors above so the border is applied on top.
                    {
                        selector:
                            'node[author_name], node[company_name], node[conference_name], node[type = "reference"][paper_id]',
                        style: {
                            'border-width': 3,
                            'border-color': '#1d4ed8',
                            cursor: 'pointer',
                        },
                    },
                ]}
            />
        </Paper>
    )
}
