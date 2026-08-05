export interface Source {
  title: string;
  url: string;
  publisher: string;
}

export interface Article {
  id: number;
  rank: number;
  category: string;
  headline: string;
  dek: string;
  body: string;
  importance: number;
  sources: Source[];
}

export interface EditionSummary {
  id: number;
  date: string;
  title: string;
  intro: string;
  status: string;
  model: string;
  article_count: number;
}

export interface Edition extends EditionSummary {
  articles: Article[];
}

export interface PipelineStatus {
  status: "idle" | "running" | "done" | "error";
  started_at: string | null;
  finished_at: string | null;
  date: string | null;
  edition_id: number | null;
  article_count: number;
  candidate_count: number;
  model: string;
  detail: string;
}
