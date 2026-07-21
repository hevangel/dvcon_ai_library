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
    tei_path?: string | null
}

export interface MarkdownResponse {
    paper_id: number
    title: string
    markdown: string
    markdown_path: string
}

export type GraphNodeKind = 'paper' | 'author' | 'company' | 'conference' | 'reference'

/**
 * A single graph node or edge payload. Node payloads carry `id`, `label`,
 * `type`, and optional click-target fields (e.g. `paper_id` for a resolved
 * reference, `author_name` / `company_name` for free-text search, or
 * `year` + `location` for a conference filter). Edge payloads carry
 * `source`, `target`, and `label`.
 */
export interface GraphElementData {
    id: string
    label?: string
    type?: GraphNodeKind
    // Edge-only fields
    source?: string
    target?: string
    // Node click-target payload fields
    paper_id?: number
    author_name?: string
    company_name?: string
    conference_name?: string
    year?: number
    location?: string
    reference_id?: number
}

export interface GraphElement {
    data: GraphElementData
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
