import { api } from "./api";

export type RefusalReason = "insufficient_history" | "out_of_scope" | "no_matching_records" | "error";

export interface Retrieval {
  tool: string;
  title: string;
  args: Record<string, unknown>;
  engine: string;
  row_count: number;
  columns: string[];
  rows: Record<string, unknown>[];
  grounded?: boolean | null;
  sources?: { tool: string; title: string; args: Record<string, unknown>; row_count: number }[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  was_refused: boolean;
  refusal_reason: RefusalReason | null;
  retrieval: Retrieval | null;
  latency_ms: number | null;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface AssistantInfo {
  suggestions: string[];
  engine: "gemini" | "rules";
  model: string | null;
}

export const getAssistantInfo = (signal?: AbortSignal) => api.get<AssistantInfo>("/assistant/info", { signal }).then((r) => r.data);
export const getSessions = (signal?: AbortSignal) => api.get<ChatSession[]>("/assistant/sessions", { signal }).then((r) => r.data);
export const getSession = (id: string, signal?: AbortSignal) =>
  api.get<ChatSession & { messages: ChatMessage[] }>(`/assistant/sessions/${id}`, { signal }).then((r) => r.data);
export const renameSession = (id: string, title: string) => api.patch<ChatSession>(`/assistant/sessions/${id}`, { title }).then((r) => r.data);
export const deleteSession = (id: string) => api.delete(`/assistant/sessions/${id}`);
export const askAssistant = (content: string, sessionId: string | null) =>
  api
    .post<{ session: ChatSession; question: ChatMessage; answer: ChatMessage }>("/assistant/ask", { content, session_id: sessionId })
    .then((r) => r.data);
