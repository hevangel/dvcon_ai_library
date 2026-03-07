import { Paper, Typography } from '@mui/material'
import CytoscapeComponent from 'react-cytoscapejs'

import type { GraphResponse, PaperDetailResponse } from '../types/api'

interface GraphTabProps {
    paper?: PaperDetailResponse
    graph?: GraphResponse
}

export function GraphTab({ paper, graph }: GraphTabProps) {
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
        <Paper variant="outlined" sx={{ height: '100%', overflow: 'hidden' }}>
            <CytoscapeComponent
                elements={[...graph.nodes, ...graph.edges]}
                style={{ width: '100%', height: '100%' }}
                layout={{ name: 'breadthfirst', directed: true, padding: 24 }}
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
                ]}
            />
        </Paper>
    )
}
