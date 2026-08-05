import ReactMarkdown from "react-markdown";
import type { Article } from "../types";
import { hostname } from "../lib/format";
import { useI18n } from "../i18n";

function Kicker({ article }: { article: Article }) {
  const { t, category } = useI18n();
  return (
    <div className="flex flex-wrap items-center gap-2 mb-2">
      {article.importance === 5 && (
        <span className="kicker text-[10px] font-bold text-[var(--paper)] bg-[var(--accent)] px-1.5 py-0.5">
          {t("starEdition")}
        </span>
      )}
      <span className="kicker text-[11px] text-[var(--accent)] font-bold">
        {category(article.category)}
      </span>
      <span className="text-[var(--rule)]">•</span>
      <span
        className="kicker text-[11px] text-[var(--muted)]"
        aria-label={t("importanceAria", { n: article.importance })}
      >
        <span aria-hidden="true">
          {"★".repeat(article.importance)}
          <span className="opacity-30">{"★".repeat(5 - article.importance)}</span>
        </span>
      </span>
    </div>
  );
}

function Sources({ article }: { article: Article }) {
  const { t } = useI18n();
  if (!article.sources.length) return null;
  return (
    <div className="mt-3 pt-2 border-t border-[var(--rule)]">
      <span className="kicker text-[11px] text-[var(--muted)]">{t("sources")} </span>
      {article.sources.map((s, i) => (
        <span key={s.url} className="text-xs">
          {i > 0 && <span className="text-[var(--muted)]"> · </span>}
          <a
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--accent)] hover:underline"
          >
            {s.publisher || hostname(s.url)}
          </a>
        </span>
      ))}
    </div>
  );
}

export function LeadStory({ article }: { article: Article }) {
  return (
    <article className="pb-6 mb-8 border-b-2 border-[var(--ink)]">
      <Kicker article={article} />
      <h2 className="headline text-[1.75rem] leading-[1.08] sm:text-4xl lg:text-5xl font-black mb-2">
        {article.headline}
      </h2>
      {article.dek && (
        <p className="text-lg italic text-[var(--muted)] mb-3 leading-snug">{article.dek}</p>
      )}
      <div className="article-body drop-cap text-[16px] md:columns-2 md:gap-8">
        <ReactMarkdown>{article.body}</ReactMarkdown>
      </div>
      <Sources article={article} />
    </article>
  );
}

export function ArticleCard({ article }: { article: Article }) {
  return (
    <article className="break-inside-avoid mb-6 pb-6 border-b border-[var(--rule)] last:border-0">
      <Kicker article={article} />
      <h3 className="headline text-[1.35rem] leading-snug font-bold mb-1">{article.headline}</h3>
      {article.dek && (
        <p className="text-sm italic text-[var(--muted)] mb-2 leading-snug">{article.dek}</p>
      )}
      <div className="article-body text-[15px]">
        <ReactMarkdown>{article.body}</ReactMarkdown>
      </div>
      <Sources article={article} />
    </article>
  );
}
