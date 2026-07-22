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

export function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}

export function assetUrl(path: string | null | undefined) {
  if (!path) return path ?? "";
  if (path.startsWith("http")) return path;
  return apiUrl(path);
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

export async function resetChat(session_id: string) {
  await fetch(apiUrl("/api/chat/reset"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id }),
  });
}
