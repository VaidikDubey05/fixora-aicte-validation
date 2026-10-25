import { useMutation } from '@tanstack/react-query';
import api from '../lib/api';

export interface CitationItem {
  chunk_id?: string;
  section: string;
  chapter?: string;
  page: number;
  snippet: string;
  relevance_score?: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatPayload {
  message: string;
  application_id?: string;
  history?: ChatMessage[];
}

export interface ChatResponse {
  response: string;
  citations: CitationItem[];
  application_id?: string;
  reply?: string;
  clause_citation?: string;
}

export function useChat() {
  return useMutation({
    mutationFn: async (payload: ChatPayload): Promise<ChatResponse> => {
      const res = await api.post<ChatResponse>('/chat', payload);
      return res.data;
    },
  });
}
