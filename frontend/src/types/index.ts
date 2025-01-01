export interface Field {
    name: string;
    type: 'string' | 'array' | 'date';
    description?: string;
  }
  
  export interface Template {
    name: string;
    description: string;
    fields: Field[];
    instructions: string;
  }
  
  export interface SearchResult {
    id: string;
    content: string;
    timestamp: string;
    artifactId: string;
    fileName: string;
    score: number;
    segmentTimestamp?: string;
    headers?: Record<string, string>;
  }
  
  export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
  }