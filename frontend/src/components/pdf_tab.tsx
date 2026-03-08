import DownloadIcon from '@mui/icons-material/Download'
import { Box, Button, Paper, Stack, Tooltip, Typography } from '@mui/material'
import { useLayoutEffect, useRef, useState } from 'react'
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
    const [page_width, set_page_width] = useState(0)
    const pdf_container_ref = useRef<HTMLDivElement | null>(null)

    useLayoutEffect(() => {
        const container = pdf_container_ref.current
        if (!container) {
            return
        }

        const update_page_width = () => {
            set_page_width(Math.max(0, Math.floor(container.getBoundingClientRect().width)))
        }

        update_page_width()

        const observer = new ResizeObserver(() => {
            update_page_width()
        })
        observer.observe(container)

        return () => {
            observer.disconnect()
        }
    }, [])

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
                sx={{ minWidth: 0 }}
            >
                <Typography variant="h6" sx={{ minWidth: 0, overflowWrap: 'anywhere' }}>
                    {paper.title}
                </Typography>
                <Stack
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    sx={{ flexWrap: 'wrap', rowGap: 1, minWidth: 0 }}
                >
                    <Stack
                        direction="row"
                        spacing={1}
                        alignItems="center"
                        sx={{ flexWrap: 'wrap', rowGap: 1, whiteSpace: 'nowrap' }}
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
                ref={pdf_container_ref}
                sx={{
                    flex: 1,
                    overflowX: 'hidden',
                    overflowY: 'auto',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 2,
                    backgroundColor: '#f5f7fb',
                }}
            >
                <Box sx={{ minWidth: 0, width: '100%', display: 'flex', justifyContent: 'center' }}>
                    <Document
                        file={pdf_url}
                        onLoadSuccess={({ numPages }) => {
                            set_page_count(numPages)
                            set_page_number(1)
                        }}
                        loading="Loading PDF..."
                    >
                        {page_width > 0 ? (
                            <Page
                                pageNumber={page_number}
                                renderAnnotationLayer={false}
                                renderTextLayer={false}
                                width={page_width}
                            />
                        ) : null}
                    </Document>
                </Box>
            </Box>
        </Stack>
    )
}
