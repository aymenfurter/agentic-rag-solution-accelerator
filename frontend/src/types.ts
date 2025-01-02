export interface Field {
    name: string;
    type: string;
    description: string;
    method: string;
    items?: {
        type: string;
        method: string;
    };
}

export interface Template {
    id: string;
    name: string;
    description: string;
    scenario: string;
    fields: Field[];
    instructions: string;
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