import axios from 'axios'

import type {
    ChatMessage,
    ChatResponse,
    GraphResponse,
    MarkdownResponse,
    PaperDetailResponse,
    SearchMode,
    SearchResponse,
    StatsResponse,
} from '../types/api'

const api_base_url = import.meta.env.VITE_API_BASE_URL ?? '/api'

export const api_client = axios.create({
    baseURL: api_base_url,
})

export function build_pdf_url(paper_id: number): string {
    return `${api_base_url}/papers/${paper_id}/pdf`
}

export async function fetch_stats(): Promise<StatsResponse> {
    const response = await api_client.get<StatsResponse>('/stats')
    return response.data
}

export async function fetch_search_results(params: {
    query: string
    mode: SearchMode
    year?: number
    location?: string
}): Promise<SearchResponse> {
    const response = await api_client.get<SearchResponse>('/search', { params })
    return response.data
}

export async function fetch_paper_detail(paper_id: number): Promise<PaperDetailResponse> {
    const response = await api_client.get<PaperDetailResponse>(`/papers/${paper_id}`)
    return response.data
}

export async function fetch_markdown(paper_id: number): Promise<MarkdownResponse> {
    const response = await api_client.get<MarkdownResponse>(`/papers/${paper_id}/markdown`)
    return response.data
}

export async function fetch_graph(paper_id: number): Promise<GraphResponse> {
    const response = await api_client.get<GraphResponse>(`/papers/${paper_id}/graph`)
    return response.data
}

export async function send_chat(payload: {
    selected_paper_ids: number[]
    messages: ChatMessage[]
}): Promise<ChatResponse> {
    const response = await api_client.post<ChatResponse>('/chat', payload)
    return response.data
}
