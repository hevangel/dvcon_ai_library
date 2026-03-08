import DownloadIcon from '@mui/icons-material/Download'
import { Box, Button, Paper, Stack, Tooltip, Typography } from '@mui/material'
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
    const pager_button_sx = { minWidth: 0, width: 36, minHeight: 36, height: 36, p: 0 }

    return (
        <Stack spacing={2} sx={{ height: '100%' }}>
            <Stack
                direction={{ xs: 'column', md: 'row' }}
                spacing={1.5}
                justifyContent="space-between"
                alignItems={{ xs: 'flex-start', md: 'center' }}
            >
                <Typography variant="h6">{paper.title}</Typography>
                <Stack
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    sx={{ flexWrap: 'wrap', rowGap: 1 }}
                >
                    <Stack
                        direction="row"
                        spacing={1}
                        alignItems="center"
                        sx={{ flexWrap: 'nowrap', whiteSpace: 'nowrap' }}
                    >
                        <Button
                            variant="outlined"
                            disabled={page_number <= 1}
                            onClick={() => set_page_number((value) => value - 1)}
                            sx={pager_button_sx}
                        >
                            {'<'}
                        </Button>
                        <Typography color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
                            Page {page_number} of {page_count || '--'}
                        </Typography>
                        <Button
                            variant="outlined"
                            disabled={page_count === 0 || page_number >= page_count}
                            onClick={() => set_page_number((value) => value + 1)}
                            sx={pager_button_sx}
                        >
                            {'>'}
                        </Button>
                        <Tooltip title="Download PDF">
                            <span>
                                <Button
                                    component="a"
                                    href={pdf_url}
                                    download
                                    variant="outlined"
                                    aria-label="Download PDF"
                                    sx={pager_button_sx}
                                >
                                    <DownloadIcon fontSize="small" />
                                </Button>
                            </span>
                        </Tooltip>
                    </Stack>
                </Stack>
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
                        renderTextLayer={false}
                        width={900}
                    />
                </Document>
            </Box>
        </Stack>
    )
}
