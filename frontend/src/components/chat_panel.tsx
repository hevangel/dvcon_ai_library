import SendIcon from '@mui/icons-material/Send'
import {
    Alert,
    Box,
    Button,
    Chip,
    Divider,
    Paper,
    Stack,
    TextField,
    Typography,
} from '@mui/material'
import { useState } from 'react'

import type { ChatCitation, ChatMessage, SearchResultItem } from '../types/api'

interface ChatPanelProps {
    messages: ChatMessage[]
    citations: ChatCitation[]
    is_loading: boolean
    selected_papers: SearchResultItem[]
    error_message?: string
    on_submit: (message: string) => Promise<void>
}

export function ChatPanel({
    messages,
    citations,
    is_loading,
    selected_papers,
    error_message,
    on_submit,
}: ChatPanelProps) {
    const [draft, set_draft] = useState('')

    async function handle_submit() {
        const trimmed = draft.trim()
        if (!trimmed) {
            return
        }

        set_draft('')
        await on_submit(trimmed)
    }

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
                        selected_papers.map((paper) => (
                            <Chip
                                key={paper.paper_id}
                                label={`${paper.title} (${paper.year})`}
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
                {messages.length === 0 ? (
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

                {citations.length > 0 ? (
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                        {citations.map((citation) => (
                            <Chip
                                key={`${citation.title}-${citation.year}`}
                                label={`${citation.title} (${citation.year})`}
                                size="small"
                                variant="outlined"
                            />
                        ))}
                    </Stack>
                ) : null}
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
                        endIcon={<SendIcon />}
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
