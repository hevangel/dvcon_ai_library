import { Box, Paper, Typography } from '@mui/material'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { build_asset_url } from '../api/client'
import type { MarkdownResponse, PaperDetailResponse } from '../types/api'

interface MarkdownTabProps {
    paper?: PaperDetailResponse
    markdown?: MarkdownResponse
}

export function MarkdownTab({ paper, markdown }: MarkdownTabProps) {
    if (!paper) {
        return (
            <Paper variant="outlined" sx={{ p: 4, height: '100%' }}>
                <Typography color="text.secondary">
                    Select a paper to review the extracted markdown and embedded diagrams.
                </Typography>
            </Paper>
        )
    }

    if (!markdown) {
        return (
            <Paper variant="outlined" sx={{ p: 4, height: '100%' }}>
                <Typography color="text.secondary">Markdown extraction has not been generated yet.</Typography>
            </Paper>
        )
    }

    return (
        <Box
            sx={{
                height: '100%',
                overflow: 'auto',
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 2,
                p: 3,
                '& img': {
                    display: 'block',
                    maxWidth: '100%',
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'divider',
                    marginBlock: 2,
                },
                '& table': {
                    borderCollapse: 'collapse',
                    width: '100%',
                    marginBlock: 2,
                },
                '& th, & td': {
                    border: '1px solid #d0d7de',
                    padding: '8px',
                    textAlign: 'left',
                },
            }}
        >
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    img: ({ src = '', alt = '', ...props }) => (
                        <Box
                            component="img"
                            src={build_asset_url(src, markdown.markdown_path)}
                            alt={alt}
                            loading="lazy"
                            {...props}
                        />
                    ),
                }}
            >
                {markdown.markdown}
            </ReactMarkdown>
        </Box>
    )
}
