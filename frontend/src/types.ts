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
    role: string;
    content: string;
    timestamp: string;
    steps?: RunStep[];  // Replace toolCalls with steps
    audioUrl?: string;
    jumpTime?: number;
}

export interface ToolCall {
    name: string;
    parameters: {
        searchText?: string;
        filter?: string;
        outputqueueuri?: string;
    };
    status: 'pending' | 'completed';
}

export interface RunStatus {
    status: 'queued' | 'in_progress' | 'requires_action' | 'completed' | 'failed';
    toolCalls?: ToolCall[];
}

export interface RunStep {
    type: string;
    status: string;
    detail_type?: string;
    tool_calls?: ToolCall[];
}