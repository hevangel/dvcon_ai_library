import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore'
import NavigateNextIcon from '@mui/icons-material/NavigateNext'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { Box, Button, Paper, Stack, Typography } from '@mui/material'
import { useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'

import { build_pdf_url } from '../api/client'
import type { PaperDetailResponse } from '../types/api'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
).toString()

interface PdfTabProps {
    paper?: PaperDetailResponse
}

export function PdfTab({ paper }: PdfTabProps) {
    const [page_count, set_page_count] = useState(0)
    const [page_number, set_page_number] = useState(1)

    if (!paper) {
        return (
            <Paper variant="outlined" sx={{ p: 4, height: '100%' }}>
                <Typography color="text.secondary">
                    Select a paper from the search results to review the PDF.
                </Typography>
            </Paper>
        )
    }

    const pdf_url = build_pdf_url(paper.paper_id)

    return (
        <Stack spacing={2} sx={{ height: '100%' }}>
            <Stack direction="row" spacing={1} justifyContent="space-between" alignItems="center">
                <Typography variant="h6">{paper.title}</Typography>
                <Button
                    href={pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    endIcon={<OpenInNewIcon />}
                    variant="outlined"
                >
                    Open PDF
                </Button>
            </Stack>
            <Stack direction="row" spacing={1} alignItems="center">
                <Button
                    variant="outlined"
                    startIcon={<NavigateBeforeIcon />}
                    disabled={page_number <= 1}
                    onClick={() => set_page_number((value) => value - 1)}
                >
                    Previous
                </Button>
                <Typography color="text.secondary">
                    Page {page_number} of {page_count || '--'}
                </Typography>
                <Button
                    variant="outlined"
                    endIcon={<NavigateNextIcon />}
                    disabled={page_count === 0 || page_number >= page_count}
                    onClick={() => set_page_number((value) => value + 1)}
                >
                    Next
                </Button>
            </Stack>
            <Box
                sx={{
                    flex: 1,
                    overflow: 'auto',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 2,
                    backgroundColor: '#f5f7fb',
                    p: 2,
                }}
            >
                <Document
                    file={pdf_url}
                    onLoadSuccess={({ numPages }) => {
                        set_page_count(numPages)
                        set_page_number(1)
                    }}
                    loading="Loading PDF..."
                >
                    <Page
                        pageNumber={page_number}
                        renderAnnotationLayer={false}
                        renderTextLayer
                        width={900}
                    />
                </Document>
            </Box>
        </Stack>
    )
}
