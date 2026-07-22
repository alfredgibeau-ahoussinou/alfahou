export const API_BASE =
  (import.meta.env.VITE_ALFAHOU_API as string | undefined) ||
  "https://alfahou.onrender.com";

export type Modality = "auto" | "text" | "image" | "video" | "pdf";
export type Mode = "balanced" | "creative" | "precise" | "teacher";

export type ChatResponse = {
  session_id: string;
  modality: string;
  text: string;
  file_url: string | null;
  skill: string;
  suggestions: string[];
  language: string;
  title?: string | null;
  message: string;
};

export type HealthResponse = {
  ok: boolean;
  device: string;
  models?: {
    llm?: {
      enabled?: boolean;
      provider?: string | null;
      model?: string | null;
    };
  };
};

export type SessionSummary = {
  id: string;
  title: string;
  updated_at: string;
  created_at: string;
  preview: string;
  message_count: number;
  mode: string;
  language: string;
};

export type SessionDetail = SessionSummary & {
  messages: Array<{
    role: string;
    content: string;
    modality?: string;
    file_url?: string | null;
    created_at?: string;
  }>;
  memory?: Record<string, unknown>;
};

const OWNED_KEY = "alfahou_owned_sessions";
const ACTIVE_KEY = "alfahou_session";

export function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}

export function assetUrl(path: string | null | undefined) {
  if (!path) return path ?? "";
  if (path.startsWith("http")) return path;
  return apiUrl(path);
}

export function getOwnedSessionIds(): string[] {
  try {
    const raw = localStorage.getItem(OWNED_KEY);
    const ids = raw ? (JSON.parse(raw) as string[]) : [];
    return Array.isArray(ids) ? ids.filter(Boolean) : [];
  } catch {
    return [];
  }
}

export function rememberSessionId(id: string) {
  const ids = getOwnedSessionIds();
  const next = [id, ...ids.filter((x) => x !== id)];
  localStorage.setItem(OWNED_KEY, JSON.stringify(next.slice(0, 80)));
  localStorage.setItem(ACTIVE_KEY, id);
}

export function forgetSessionId(id: string) {
  const ids = getOwnedSessionIds().filter((x) => x !== id);
  localStorage.setItem(OWNED_KEY, JSON.stringify(ids));
  if (localStorage.getItem(ACTIVE_KEY) === id) {
    localStorage.removeItem(ACTIVE_KEY);
  }
}

export function getActiveSessionId(): string | null {
  return localStorage.getItem(ACTIVE_KEY);
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(apiUrl("/api/health"));
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function sendChat(input: {
  prompt: string;
  session_id: string | null;
  modality: Modality;
  mode: Mode;
}): Promise<ChatResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120_000);
  try {
    const res = await fetch(apiUrl("/api/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || data.message || `HTTP ${res.status}`);
    }
    return data as ChatResponse;
  } finally {
    clearTimeout(timeout);
  }
}

export async function createSession(input?: {
  title?: string;
  mode?: Mode;
  language?: string;
}): Promise<SessionDetail> {
  const res = await fetch(apiUrl("/api/chat/sessions"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data as SessionDetail;
}

export async function listOwnedSessions(): Promise<SessionSummary[]> {
  const ids = getOwnedSessionIds();
  if (!ids.length) return [];
  const res = await fetch(apiUrl("/api/chat/sessions/list"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return (data.sessions || []) as SessionSummary[];
}

export async function fetchSession(session_id: string): Promise<SessionDetail> {
  const res = await fetch(apiUrl(`/api/chat/sessions/${session_id}`));
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data as SessionDetail;
}

export async function deleteSession(session_id: string): Promise<void> {
  const res = await fetch(apiUrl(`/api/chat/sessions/${session_id}`), { method: "DELETE" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  forgetSessionId(session_id);
}

export async function renameSession(session_id: string, title: string): Promise<void> {
  const res = await fetch(apiUrl(`/api/chat/sessions/${session_id}`), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
}

export async function resetChat(session_id: string) {
  await fetch(apiUrl("/api/chat/reset"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id }),
  });
}
