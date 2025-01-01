import { Field } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const setupAgent = async (fields: Field[], template?: string) => {
  const response = await fetch(`${BASE_URL}/api/setupAgent`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fields, template })
  });
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
  return response.json();
};

export const searchArtifacts = async (params: {
  searchText: string;
  filter?: string;
  semanticRanking?: boolean;
  topK?: number;
}) => {
  const response = await fetch(`${BASE_URL}/api/artifact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payload: params })
  });
  return response.json();
};

export const searchChunks = async (params: {
  searchText: string;
  filter?: string;
  semanticRanking?: boolean;
  questionRewriting?: boolean;
  topK?: number;
}) => {
  const response = await fetch(`${BASE_URL}/api/artifactchunk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payload: params })
  });
  return response.json();
};