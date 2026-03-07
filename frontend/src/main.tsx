import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'
import './index.css'

const query_client = new QueryClient()

const app_theme = createTheme({
    palette: {
        primary: {
            main: '#1d4ed8',
        },
        secondary: {
            main: '#0f766e',
        },
        background: {
            default: '#eef2f7',
            paper: '#ffffff',
        },
    },
    shape: {
        borderRadius: 14,
    },
    typography: {
        fontFamily: ['Inter', 'Segoe UI', 'Roboto', 'sans-serif'].join(','),
    },
})

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <QueryClientProvider client={query_client}>
            <ThemeProvider theme={app_theme}>
                <CssBaseline />
                <App />
            </ThemeProvider>
        </QueryClientProvider>
    </StrictMode>,
)
