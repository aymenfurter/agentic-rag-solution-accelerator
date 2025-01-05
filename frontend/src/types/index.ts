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

export interface StepData {
  id: string;
  object: string;
  created_at: number;      // in seconds from server, we do * 1000 for ms
  completed_at: number;    // same
  run_id: string;
  assistant_id: string;
  thread_id: string;
  type: string;
  status: string;
  step_details: string;  // raw JSON
  usage: string;         // raw JSON
}

export interface Step {
  type: string;
  _data: {
    id: string;
    step_details: string;
  }
}
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  steps?: Step[];
  toolCalls?: any;
}

export interface Thread {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
}
