export interface Field {
    name: string;
    type: string;
    required: boolean;
    description?: string;
}

export interface Template {
    id: string;
    name: string;
    description: string;
    instructions: string;
    fields: Field[];
}

export interface SearchResult {
    id: string;
    content: string;
    score: number;
}

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    audioUrl?: string;
    jumpTime?: number;
}