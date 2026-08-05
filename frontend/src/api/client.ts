import type { Edition, EditionSummary, PipelineStatus } from "../types";

// In dev this stays empty and Vite proxies /api -> localhost:8000.
// In production (Vercel) set VITE_API_BASE_URL to the Coolify backend URL,
// e.g. https://ai-news-api.your-domain.com  (no trailing slash).
const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

const q = (lang?: string) => (lang ? `?lang=${encodeURIComponent(lang)}` : "");

export const api = {
  async latest(lang?: string): Promise<Edition | null> {
    const res = await fetch(`${BASE}/api/editions/latest${q(lang)}`);
    if (res.status === 404) return null;
    return json<Edition>(res);
  },

  listEditions(lang?: string): Promise<EditionSummary[]> {
    return fetch(`${BASE}/api/editions${q(lang)}`).then(json<EditionSummary[]>);
  },

  getEdition(date: string, lang?: string): Promise<Edition> {
    return fetch(`${BASE}/api/editions/${date}${q(lang)}`).then(json<Edition>);
  },

  trigger(): Promise<{ accepted: boolean } & PipelineStatus> {
    return fetch(`${BASE}/api/pipeline/trigger`, { method: "POST" }).then(
      json<{ accepted: boolean } & PipelineStatus>,
    );
  },

  status(): Promise<PipelineStatus> {
    return fetch(`${BASE}/api/pipeline/status`).then(json<PipelineStatus>);
  },
};
