import SendIcon from '@mui/icons-material/Send'
import {
    Alert,
    Box,
    Button,
    Chip,
    CircularProgress,
    Divider,
    Paper,
    Stack,
    TextField,
    Tooltip,
    Typography,
} from '@mui/material'
import { useEffect, useRef, useState } from 'react'

import type { ChatCitation, ChatMessage, SearchResultItem } from '../types/api'

const default_prompts = [
    { command: '/help', description: 'Show chat commands and usage tips.' },
    { command: '/clear', description: 'Clear the conversation and return to help.' },
    { command: '/summarize', description: 'Summarize the current paper scope in 2-3 paragraphs.' },
]

interface ChatPanelProps {
    messages: ChatMessage[]
    citations: ChatCitation[]
    show_help: boolean
    is_loading: boolean
    selected_papers: SearchResultItem[]
    error_message?: string
    on_submit: (message: string) => Promise<void>
}

export function ChatPanel({
    messages,
    citations,
    show_help,
    is_loading,
    selected_papers,
    error_message,
    on_submit,
}: ChatPanelProps) {
    const [draft, set_draft] = useState('')
    const messages_end_ref = useRef<HTMLDivElement | null>(null)

    async function handle_submit() {
        if (is_loading) {
            return
        }

        const trimmed = draft.trim()
        if (!trimmed) {
            return
        }

        set_draft('')
        await on_submit(trimmed)
    }

    useEffect(() => {
        messages_end_ref.current?.scrollIntoView({
            behavior: messages.length > 0 || is_loading ? 'smooth' : 'auto',
            block: 'end',
        })
    }, [messages.length, citations.length, is_loading, show_help])

    return (
        <Paper
            elevation={0}
            sx={{
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 3,
                overflow: 'hidden',
            }}
        >
            <Box sx={{ p: 2.5, backgroundColor: 'grey.50' }}>
                <Typography variant="h6">Contextual Paper Chat</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    Ask grounded questions against the selected DVCon papers. Responses are limited to retrieved paper context.
                </Typography>
                <Stack direction="row" spacing={1} mt={2} flexWrap="wrap" useFlexGap>
                    {selected_papers.length === 0 ? (
                        <Chip label="No papers selected" size="small" variant="outlined" />
                    ) : (
                        selected_papers.map((paper, index) => (
                            <Chip
                                key={paper.paper_id}
                                label={`[${index + 1}] ${paper.title} (${paper.year})`}
                                size="small"
                                color="primary"
                                variant="outlined"
                            />
                        ))
                    )}
                </Stack>
            </Box>

            <Divider />

            <Stack spacing={2} sx={{ flex: 1, overflow: 'auto', p: 2.5, backgroundColor: '#f8fafc' }}>
                {show_help ? (
                    <Alert severity="info" sx={{ alignItems: 'flex-start' }}>
                        <Stack spacing={1}>
                            <Typography variant="subtitle2" fontWeight={700}>
                                Chat commands
                            </Typography>
                            {default_prompts.map((prompt) => (
                                <Typography key={prompt.command} variant="body2">
                                    <Box component="span" sx={{ fontFamily: 'monospace', fontWeight: 700 }}>
                                        {prompt.command}
                                    </Box>{' '}
                                    {prompt.description}
                                </Typography>
                            ))}
                            <Typography variant="body2">
                                Ask normal questions too, such as "Compare the selected papers on formal sign-off."
                            </Typography>
                        </Stack>
                    </Alert>
                ) : null}

                {messages.length === 0 && !show_help ? (
                    <Alert severity="info">
                        Start with a question such as “Summarize the verification methodology” or “Compare the selected papers on formal sign-off.”
                    </Alert>
                ) : null}

                {messages.map((message, index) => (
                    <Box
                        key={`${message.role}-${index}`}
                        sx={{
                            alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '92%',
                            px: 2,
                            py: 1.5,
                            borderRadius: 2,
                            backgroundColor: message.role === 'user' ? 'primary.main' : 'background.paper',
                            color: message.role === 'user' ? 'primary.contrastText' : 'text.primary',
                            boxShadow: 1,
                        }}
                    >
                        <Typography variant="caption" sx={{ opacity: 0.75 }}>
                            {message.role === 'user' ? 'You' : 'Assistant'}
                        </Typography>
                        <Typography sx={{ whiteSpace: 'pre-wrap' }}>{message.content}</Typography>
                    </Box>
                ))}

                {is_loading ? (
                    <Box
                        sx={{
                            alignSelf: 'flex-start',
                            maxWidth: '92%',
                            px: 2,
                            py: 1.5,
                            borderRadius: 2,
                            backgroundColor: 'background.paper',
                            color: 'text.primary',
                            boxShadow: 1,
                        }}
                    >
                        <Typography variant="caption" sx={{ opacity: 0.75 }}>
                            Assistant
                        </Typography>
                        <Stack direction="row" spacing={1} alignItems="center">
                            <CircularProgress size={16} />
                            <Typography sx={{ whiteSpace: 'pre-wrap' }}>Thinking...</Typography>
                        </Stack>
                    </Box>
                ) : null}

                {citations.length > 0 ? (
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {citations.map((citation) => (
                            <Tooltip
                                key={`${citation.paper_id}-${citation.index}`}
                                title={`${citation.title} (${citation.year})`}
                                arrow
                            >
                                <Chip
                                    label={`[${citation.index}]`}
                                    size="small"
                                    variant="outlined"
                                />
                            </Tooltip>
                        ))}
                    </Stack>
                ) : null}
                <Box ref={messages_end_ref} />
            </Stack>

            <Divider />

            <Stack spacing={1.5} sx={{ p: 2.5 }}>
                {error_message ? <Alert severity="warning">{error_message}</Alert> : null}
                <TextField
                    multiline
                    minRows={3}
                    maxRows={8}
                    placeholder="Ask a question about the selected papers..."
                    value={draft}
                    disabled={is_loading}
                    onChange={(event) => set_draft(event.target.value)}
                    onKeyDown={(event) => {
                        if (event.key === 'Enter' && !event.shiftKey) {
                            event.preventDefault()
                            void handle_submit()
                        }
                    }}
                />
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="caption" color="text.secondary">
                        Press Enter to submit. Press Shift+Enter for a new line.
                    </Typography>
                    <Button
                        variant="contained"
                        endIcon={is_loading ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
                        onClick={() => void handle_submit()}
                        disabled={is_loading}
                    >
                        {is_loading ? 'Thinking...' : 'Submit'}
                    </Button>
                </Stack>
            </Stack>
        </Paper>
    )
}
