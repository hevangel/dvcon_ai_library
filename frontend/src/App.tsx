import {
    AppBar,
    Box,
    Chip,
    CircularProgress,
    Grid,
    Paper,
    Stack,
    Tab,
    Tabs,
    Toolbar,
    Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import { useMemo, useState } from 'react'

import {
    fetch_graph,
    fetch_markdown,
    fetch_paper_detail,
    fetch_search_results,
    fetch_stats,
    send_chat,
} from './api/client'
import { ChatPanel } from './components/chat_panel'
import { GraphTab } from './components/graph_tab'
import { MarkdownTab } from './components/markdown_tab'
import { PdfTab } from './components/pdf_tab'
import { SearchResultsTab } from './components/search_results_tab'
import type { ChatMessage, ChatCitation, SearchMode, SearchResultItem } from './types/api'

function App() {
    const [active_tab, set_active_tab] = useState(0)
    const [active_paper_id, set_active_paper_id] = useState<number | null>(null)
    const [selected_paper_ids, set_selected_paper_ids] = useState<number[]>([])
    const [chat_messages, set_chat_messages] = useState<ChatMessage[]>([])
    const [chat_citations, set_chat_citations] = useState<ChatCitation[]>([])
    const [chat_error, set_chat_error] = useState<string | undefined>(undefined)
    const [chat_loading, set_chat_loading] = useState(false)
    const [search_request, set_search_request] = useState<{
        query: string
        mode: SearchMode
        year?: number
        location?: string
    }>({
        query: '',
        mode: 'hybrid',
    })

    const stats_query = useQuery({
        queryKey: ['stats'],
        queryFn: fetch_stats,
    })

    const search_query = useQuery({
        queryKey: ['search', search_request],
        queryFn: () => fetch_search_results(search_request),
    })

    const paper_query = useQuery({
        queryKey: ['paper', active_paper_id],
        queryFn: () => fetch_paper_detail(active_paper_id ?? 0),
        enabled: active_paper_id !== null,
    })

    const markdown_query = useQuery({
        queryKey: ['markdown', active_paper_id],
        queryFn: () => fetch_markdown(active_paper_id ?? 0),
        enabled: active_paper_id !== null,
    })

    const graph_query = useQuery({
        queryKey: ['graph', active_paper_id],
        queryFn: () => fetch_graph(active_paper_id ?? 0),
        enabled: active_paper_id !== null,
    })

    const search_results = search_query.data?.items ?? []
    const active_scope_paper_ids = selected_paper_ids.length > 0
        ? selected_paper_ids
        : active_paper_id
          ? [active_paper_id]
          : []

    const selected_papers = useMemo(() => {
        const result_map = new Map(search_results.map((paper) => [paper.paper_id, paper]))
        const papers: SearchResultItem[] = []

        for (const paper_id of active_scope_paper_ids) {
            const paper = result_map.get(paper_id)
            if (paper) {
                papers.push(paper)
            }
        }

        if (
            papers.length === 0 &&
            paper_query.data &&
            active_scope_paper_ids.includes(paper_query.data.paper_id)
        ) {
            papers.push({
                paper_id: paper_query.data.paper_id,
                title: paper_query.data.title,
                abstract: paper_query.data.abstract,
                authors: paper_query.data.authors,
                affiliations: paper_query.data.affiliations,
                year: paper_query.data.year,
                location: paper_query.data.location,
                conference_name: paper_query.data.conference_name,
                score: 0,
                snippet: paper_query.data.abstract,
            })
        }

        return papers
    }, [active_scope_paper_ids, paper_query.data, search_results])

    async function handle_chat_submit(message: string) {
        set_chat_loading(true)
        set_chat_error(undefined)
        const next_messages = [...chat_messages, { role: 'user', content: message } satisfies ChatMessage]
        set_chat_messages(next_messages)

        try {
            const response = await send_chat({
                selected_paper_ids: active_scope_paper_ids,
                messages: next_messages,
            })
            set_chat_messages([
                ...next_messages,
                { role: 'assistant', content: response.answer },
            ])
            set_chat_citations(response.citations)
        } catch (error) {
            if (axios.isAxiosError(error)) {
                set_chat_error(error.response?.data?.detail ?? 'Unable to complete the chat request.')
            } else {
                set_chat_error('Unable to complete the chat request.')
            }
        } finally {
            set_chat_loading(false)
        }
    }

    return (
        <Box sx={{ minHeight: '100vh', backgroundColor: '#eef2f7' }}>
            <AppBar position="static" elevation={0} sx={{ background: 'linear-gradient(90deg, #0f172a 0%, #1d4ed8 100%)' }}>
                <Toolbar sx={{ alignItems: 'flex-start', py: 2 }}>
                    <Stack spacing={1}>
                        <Typography variant="h4" fontWeight={700}>
                            DVCon Proceedings Intelligence Portal
                        </Typography>
                        <Typography variant="body1" sx={{ maxWidth: 980, opacity: 0.92 }}>
                            {stats_query.data
                                ? `Search across ${stats_query.data.paper_count} papers spanning ${stats_query.data.year_count} years and ${stats_query.data.conference_count} conference collections with keyword, semantic, and grounded chat workflows.`
                                : 'Search DVCon papers, inspect primary sources, and chat with grounded paper context.'}
                        </Typography>
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            <Chip label={`${stats_query.data?.paper_count ?? '--'} papers`} color="primary" variant="filled" />
                            <Chip label={`${stats_query.data?.year_count ?? '--'} years`} color="primary" variant="filled" />
                            <Chip label={`${stats_query.data?.conference_count ?? '--'} conferences`} color="primary" variant="filled" />
                        </Stack>
                    </Stack>
                </Toolbar>
            </AppBar>

            <Box sx={{ p: 2.5 }}>
                <Grid container spacing={2.5} sx={{ minHeight: 'calc(100vh - 170px)' }}>
                    <Grid size={{ xs: 12, lg: 7 }}>
                        <Paper
                            elevation={0}
                            sx={{
                                display: 'flex',
                                flexDirection: 'column',
                                height: '100%',
                                border: '1px solid',
                                borderColor: 'divider',
                                borderRadius: 3,
                            }}
                        >
                            <Tabs
                                value={active_tab}
                                onChange={(_, value) => set_active_tab(value)}
                                variant="scrollable"
                                sx={{ borderBottom: '1px solid', borderColor: 'divider' }}
                            >
                                <Tab label="Search Results" />
                                <Tab label="PDF" />
                                <Tab label="Markdown" />
                                <Tab label="Metadata Graph" />
                            </Tabs>

                            <Box sx={{ p: 2.5, flex: 1, minHeight: 0 }}>
                                {active_tab === 0 ? (
                                    <SearchResultsTab
                                        stats={stats_query.data}
                                        loading={search_query.isLoading}
                                        results={search_results}
                                        active_paper_id={active_paper_id}
                                        selected_paper_ids={selected_paper_ids}
                                        initial_query={search_request.query}
                                        initial_mode={search_request.mode}
                                        initial_year={search_request.year}
                                        initial_location={search_request.location}
                                        on_search={(payload) => set_search_request(payload)}
                                        on_toggle_paper={(paper_id) => {
                                            set_selected_paper_ids((current) =>
                                                current.includes(paper_id)
                                                    ? current.filter((item) => item !== paper_id)
                                                    : [...current, paper_id],
                                            )
                                        }}
                                        on_activate_paper={(paper_id) => {
                                            set_active_paper_id(paper_id)
                                            set_active_tab(1)
                                        }}
                                    />
                                ) : null}

                                {active_tab === 1 ? <PdfTab paper={paper_query.data} /> : null}
                                {active_tab === 2 ? <MarkdownTab paper={paper_query.data} markdown={markdown_query.data} /> : null}
                                {active_tab === 3 ? <GraphTab paper={paper_query.data} graph={graph_query.data} /> : null}
                            </Box>
                        </Paper>
                    </Grid>

                    <Grid size={{ xs: 12, lg: 5 }}>
                        <ChatPanel
                            messages={chat_messages}
                            citations={chat_citations}
                            is_loading={chat_loading}
                            error_message={chat_error}
                            selected_papers={selected_papers}
                            on_submit={handle_chat_submit}
                        />
                    </Grid>
                </Grid>
            </Box>

            {(stats_query.isLoading || search_query.isLoading) && (
                <Stack
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    sx={{
                        position: 'fixed',
                        right: 20,
                        bottom: 20,
                        px: 2,
                        py: 1,
                        borderRadius: 99,
                        backgroundColor: 'background.paper',
                        boxShadow: 3,
                    }}
                >
                    <CircularProgress size={18} />
                    <Typography variant="body2">Loading corpus data...</Typography>
                </Stack>
            )}
        </Box>
    )
}

export default App
