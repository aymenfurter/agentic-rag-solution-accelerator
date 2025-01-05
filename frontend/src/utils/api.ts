import { Field } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

interface SetupAgentRequest {
  name: string;
  fields: any[];
  scenario: string;
  instructions: string;
}

export const setupAgent = async (request: SetupAgentRequest) => {
  const response = await fetch(`${BASE_URL}/api/agent/setup`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Setup failed: ${response.statusText}`);
  }

  return response.json();
};

export const uploadFile = async (file: File, metadata: Record<string, any>) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('metadata', JSON.stringify(metadata));

  const response = await fetch(`${BASE_URL}/api/uploadFile`, {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Upload failed: ${response.status} ${errorText || response.statusText}`);
  }

  return response.json();
};

export const sendChatMessage = async (prompt: string, threadId: string) => {
  const response = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ prompt, threadId }),
  });

  if (!response.ok) {
    throw new Error(`Chat failed: ${response.statusText}`);
  }

  return response.json();
};

export const loadChatHistory = async (threadId: string) => {
  const response = await fetch(`${BASE_URL}/api/chat/history/${threadId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to load chat history: ${response.statusText}`);
  }

  return response.json();
};

export const createChatThread = async () => {
  const response = await fetch(`${BASE_URL}/api/chat/thread`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to create chat thread: ${response.statusText}`);
  }

  return response.json();
};

export const checkSetupStatus = async () => {
  const response = await fetch(`${BASE_URL}/api/agent/setup/status`, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new Error(`Failed to check setup status: ${response.statusText}`);
  }

  return response.json();
};

export const getFile = async (filename: string): Promise<Blob> => {
  const response = await fetch(`/api/getFile/${encodeURIComponent(filename)}`, {
    method: 'GET',
    headers: {
      // Add any auth headers if needed
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to download file: ${response.statusText}`);
  }

  return response.blob();
};