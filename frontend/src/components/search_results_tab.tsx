import SearchIcon from '@mui/icons-material/Search'
import {
    Box,
    Button,
    Checkbox,
    Chip,
    Divider,
    FormControl,
    InputAdornment,
    InputLabel,
    List,
    ListItemButton,
    ListItemText,
    MenuItem,
    Paper,
    Select,
    Stack,
    TextField,
    ToggleButton,
    ToggleButtonGroup,
    Typography,
} from '@mui/material'
import { useEffect, useState } from 'react'

import type { SearchMode, SearchResultItem, StatsResponse } from '../types/api'

interface SearchResultsTabProps {
    stats?: StatsResponse
    loading: boolean
    results: SearchResultItem[]
    active_paper_id: number | null
    selected_paper_ids: number[]
    initial_query: string
    initial_mode: SearchMode
    initial_year?: number
    initial_location?: string
    on_search: (payload: {
        query: string
        mode: SearchMode
        year?: number
        location?: string
    }) => void
    on_toggle_paper: (paper_id: number) => void
    on_activate_paper: (paper_id: number) => void
}

export function SearchResultsTab({
    stats,
    loading,
    results,
    active_paper_id,
    selected_paper_ids,
    initial_query,
    initial_mode,
    initial_year,
    initial_location,
    on_search,
    on_toggle_paper,
    on_activate_paper,
}: SearchResultsTabProps) {
    const [query, set_query] = useState(initial_query)
    const [mode, set_mode] = useState<SearchMode>(initial_mode)
    const [year, set_year] = useState<number | ''>(initial_year ?? '')
    const [location, set_location] = useState(initial_location ?? '')

    useEffect(() => {
        set_query(initial_query)
        set_mode(initial_mode)
        set_year(initial_year ?? '')
        set_location(initial_location ?? '')
    }, [initial_location, initial_mode, initial_query, initial_year])

    return (
        <Stack spacing={2} sx={{ height: '100%', minHeight: 0 }}>
            <Paper
                component="form"
                onSubmit={(event) => {
                    event.preventDefault()
                    on_search({
                        query,
                        mode,
                        year: year === '' ? undefined : year,
                        location: location || undefined,
                    })
                }}
                elevation={0}
                sx={{
                    p: 2,
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 3,
                    background: 'linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(248,250,252,1) 100%)',
                }}
            >
                <Stack spacing={2}>
                    <TextField
                        fullWidth
                        label="Search DVCon papers"
                        placeholder="Keyword phrase, topic, method, protocol, or verification challenge"
                        value={query}
                        onChange={(event) => set_query(event.target.value)}
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <SearchIcon color="action" />
                                </InputAdornment>
                            ),
                        }}
                        sx={{
                            '& .MuiOutlinedInput-root': {
                                borderRadius: 999,
                                backgroundColor: 'background.paper',
                            },
                        }}
                    />

                    <Stack direction={{ xs: 'column', xl: 'row' }} spacing={1.5} alignItems={{ xl: 'center' }}>
                        <ToggleButtonGroup
                            exclusive
                            color="primary"
                            value={mode}
                            onChange={(_, value: SearchMode | null) => {
                                if (value) {
                                    set_mode(value)
                                }
                            }}
                            sx={{
                                flexWrap: 'wrap',
                                '& .MuiToggleButton-root': {
                                    px: 2,
                                    textTransform: 'none',
                                    fontWeight: 600,
                                },
                            }}
                        >
                            <ToggleButton value="keyword">Keyword</ToggleButton>
                            <ToggleButton value="semantic">Semantic</ToggleButton>
                            <ToggleButton value="hybrid">Hybrid</ToggleButton>
                        </ToggleButtonGroup>

                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} flex={1}>
                            <FormControl
                                size="small"
                                sx={{
                                    minWidth: 130,
                                    flex: { xs: 1, sm: '0 0 140px' },
                                    '& .MuiOutlinedInput-root': { backgroundColor: 'background.paper' },
                                }}
                            >
                                <InputLabel id="year-filter-label">Year</InputLabel>
                                <Select
                                    labelId="year-filter-label"
                                    label="Year"
                                    value={year}
                                    onChange={(event) => {
                                        const value = String(event.target.value)
                                        set_year(value === '' ? '' : Number(value))
                                    }}
                                >
                                    <MenuItem value="">All</MenuItem>
                                    {stats?.years.map((item) => (
                                        <MenuItem key={item} value={item}>
                                            {item}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>

                            <FormControl
                                size="small"
                                sx={{
                                    minWidth: 150,
                                    flex: { xs: 1, sm: '0 0 170px' },
                                    '& .MuiOutlinedInput-root': { backgroundColor: 'background.paper' },
                                }}
                            >
                                <InputLabel id="location-filter-label">Conference</InputLabel>
                                <Select
                                    labelId="location-filter-label"
                                    label="Conference"
                                    value={location}
                                    onChange={(event) => set_location(event.target.value)}
                                >
                                    <MenuItem value="">All</MenuItem>
                                    {stats?.locations.map((item) => (
                                        <MenuItem key={item} value={item}>
                                            {item}
                                        </MenuItem>
                                    ))}
                                </Select>
                            </FormControl>

                            <Button
                                type="submit"
                                variant="contained"
                                startIcon={<SearchIcon />}
                                sx={{
                                    minWidth: { xs: '100%', sm: 140 },
                                    borderRadius: 999,
                                    px: 3,
                                }}
                            >
                                Search
                            </Button>
                        </Stack>
                    </Stack>
                </Stack>
            </Paper>

            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ flexShrink: 0 }}>
                <Chip label={`${results.length} results`} variant="outlined" />
                <Chip label={`${selected_paper_ids.length} selected`} variant="outlined" />
                <Chip label={`Mode: ${mode}`} variant="outlined" />
            </Stack>

            <Box
                sx={{
                    flex: 1,
                    minHeight: 0,
                    overflow: 'hidden',
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 2,
                    backgroundColor: 'background.paper',
                }}
            >
                <List disablePadding sx={{ height: '100%', overflow: 'auto' }}>
                    {results.map((paper, index) => {
                        const is_selected = selected_paper_ids.includes(paper.paper_id)
                        const is_active = active_paper_id === paper.paper_id
                        return (
                            <Box key={paper.paper_id}>
                                <ListItemButton
                                    selected={is_active}
                                    alignItems="flex-start"
                                    onClick={() => on_activate_paper(paper.paper_id)}
                                    sx={{ py: 2, px: 2 }}
                                >
                                    <Checkbox
                                        checked={is_selected}
                                        onClick={(event) => event.stopPropagation()}
                                        onChange={() => on_toggle_paper(paper.paper_id)}
                                        sx={{ mt: 0.25, mr: 1, flexShrink: 0, alignSelf: 'flex-start' }}
                                    />
                                    <ListItemText
                                        primary={
                                            <Stack spacing={1}>
                                                <Typography variant="subtitle1" fontWeight={600}>
                                                    {paper.title}
                                                </Typography>
                                                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                                                    <Chip label={paper.conference_name ?? `${paper.location} ${paper.year}`} size="small" />
                                                    <Chip label={`Score ${paper.score.toFixed(2)}`} size="small" variant="outlined" />
                                                </Stack>
                                            </Stack>
                                        }
                                        secondary={
                                            <Stack spacing={1} sx={{ mt: 1 }}>
                                                <Typography variant="body2" color="text.secondary">
                                                    {paper.authors.join(', ') || 'Author metadata pending'}
                                                </Typography>
                                                <Typography variant="body2">{paper.snippet || paper.abstract || 'No preview available.'}</Typography>
                                            </Stack>
                                        }
                                    />
                                </ListItemButton>
                                {index < results.length - 1 ? <Divider component="li" /> : null}
                            </Box>
                        )
                    })}
                    {!loading && results.length === 0 ? (
                        <Box sx={{ p: 4 }}>
                            <Typography color="text.secondary">
                                No papers matched the current search criteria.
                            </Typography>
                        </Box>
                    ) : null}
                    {loading ? (
                        <Box sx={{ p: 4 }}>
                            <Typography color="text.secondary">Searching the DVCon corpus...</Typography>
                        </Box>
                    ) : null}
                </List>
            </Box>
        </Stack>
    )
}
