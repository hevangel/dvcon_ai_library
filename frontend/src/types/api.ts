export type SearchMode = 'keyword' | 'semantic' | 'hybrid'

export interface StatsResponse {
    paper_count: number
    year_count: number
    conference_count: number
    years: number[]
    locations: string[]
}

export interface SearchResultItem {
    paper_id: number
    title: string
    abstract: string
    authors: string[]
    affiliations: string[]
    year: number
    location: string
    conference_name?: string | null
    score: number
    snippet: string
}

export interface SearchResponse {
    mode: SearchMode
    items: SearchResultItem[]
}

export interface PaperDetailResponse {
    paper_id: number
    title: string
    authors: string[]
    abstract: string
    affiliations: string[]
    references: string[]
    year: number
    location: string
    conference_name?: string | null
    source_url: string
    pdf_url: string
    pdf_path: string
    markdown_path?: string | null
}

export interface MarkdownResponse {
    paper_id: number
    title: string
    markdown: string
    markdown_path: string
}

export interface GraphElement {
    data: Record<string, string>
}

export interface GraphResponse {
    paper_id: number
    nodes: GraphElement[]
    edges: GraphElement[]
}

export interface ChatMessage {
    role: 'system' | 'user' | 'assistant'
    content: string
}

export interface ChatCitation {
    index: string
    paper_id: string
    title: string
    year: string
}

export interface ChatResponse {
    answer: string
    citations: ChatCitation[]
    scope_paper_ids: number[]
    response_id?: string | null
}
