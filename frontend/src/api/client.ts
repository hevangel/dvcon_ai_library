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
const backend_base_url = /^https?:\/\//.test(api_base_url)
    ? api_base_url.replace(/\/api\/?$/, '')
    : ''

function join_url_path(...parts: string[]): string {
    return parts
        .filter(Boolean)
        .map((part, index) => (index === 0 ? part.replace(/\/+$/, '') : part.replace(/^\/+|\/+$/g, '')))
        .join('/')
}

function resolve_markdown_asset_path(asset_url: string, markdown_path?: string): string {
    if (asset_url.startsWith('/')) {
        return asset_url
    }

    const normalized_asset_url = asset_url.replace(/^[.][\\/]/, '').replace(/\\/g, '/')
    const normalized_markdown_path = markdown_path?.replace(/\\/g, '/')
    const markdown_dir = normalized_markdown_path?.includes('/')
        ? normalized_markdown_path.slice(0, normalized_markdown_path.lastIndexOf('/'))
        : ''

    if (!markdown_dir) {
        return normalized_asset_url
    }

    return `/assets/${encodeURI(join_url_path(markdown_dir, normalized_asset_url))}`
}

export const api_client = axios.create({
    baseURL: api_base_url,
})

export function build_pdf_url(paper_id: number): string {
    return `${api_base_url}/papers/${paper_id}/pdf`
}

export function build_asset_url(asset_url: string, markdown_path?: string): string {
    if (!asset_url || /^([a-z]+:)?\/\//i.test(asset_url) || asset_url.startsWith('data:')) {
        return asset_url
    }

    const resolved_asset_url = resolve_markdown_asset_path(asset_url, markdown_path)

    if (!backend_base_url) {
        return resolved_asset_url
    }

    if (resolved_asset_url.startsWith('/')) {
        return `${backend_base_url}${resolved_asset_url}`
    }

    return `${backend_base_url}/${resolved_asset_url}`
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
    previous_response_id?: string
}): Promise<ChatResponse> {
    const response = await api_client.post<ChatResponse>('/chat', payload)
    return response.data
}
