import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import type { Edition, EditionSummary } from "./types";
import { useTheme } from "./hooks/useTheme";
import { useI18n } from "./i18n";
import { Masthead } from "./components/Masthead";
import { ArchiveBar } from "./components/ArchiveBar";
import { CategoryNav } from "./components/CategoryNav";
import { LeadStory, ArticleCard } from "./components/ArticleViews";
import { Skeleton } from "./components/Skeleton";
import { Footer } from "./components/Footer";
import { formatLongDate } from "./lib/format";

export default function App() {
  const { theme, cycle } = useTheme();
  const { lang, t, category } = useI18n();
  const [edition, setEdition] = useState<Edition | null>(null);
  const [editions, setEditions] = useState<EditionSummary[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null); // null = latest
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string | null>(null);

  const fetchView = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [list, ed] = await Promise.all([
        api.listEditions(lang),
        selectedDate ? api.getEdition(selectedDate, lang) : api.latest(lang),
      ]);
      setEditions(list);
      setEdition(ed);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [lang, selectedDate]);

  useEffect(() => {
    fetchView();
  }, [fetchView]);

  // Reset the section filter and update the tab title whenever the edition changes.
  useEffect(() => {
    setFilter(null);
    if (edition) {
      document.title = `${edition.title || "The Daily Model"} — ${formatLongDate(edition.date, lang)}`;
    }
  }, [edition, lang]);

  const articles = edition?.articles ?? [];
  const present = new Set(articles.map((a) => a.category));
  const filtered = filter ? articles.filter((a) => a.category === filter) : articles;
  const lead = !filter ? filtered.find((a) => a.rank === 0) : undefined;
  const river = lead ? filtered.filter((a) => a.rank !== 0) : filtered;

  const idx = edition ? editions.findIndex((e) => e.date === edition.date) : -1;
  const issueNo = idx >= 0 ? editions.length - idx : null;

  return (
    <div className="min-h-full">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-[var(--paper)] focus:border focus:border-[var(--ink)] focus:px-3 focus:py-2 kicker text-[11px]"
      >
        {t("skipLink")}
      </a>

      <div className="max-w-5xl mx-auto px-4 py-4 sm:px-6 sm:py-6">
        <Masthead
          date={edition?.date ?? null}
          subtitle={edition?.title ?? t("defaultSubtitle")}
          model={edition?.model ?? ""}
          theme={theme}
          onCycleTheme={cycle}
        />

        <ArchiveBar
          editions={editions}
          currentDate={edition?.date ?? null}
          onSelect={setSelectedDate}
        />

        {edition && articles.length > 0 && (
          <CategoryNav present={present} active={filter} onSelect={setFilter} />
        )}

        <main id="main" aria-busy={loading}>
          {loading && <Skeleton />}

          {error && !loading && (
            <div role="alert" className="text-center py-16 border-y-2 border-[var(--accent)] my-8">
              <p className="kicker text-[10px] text-[var(--accent)] mb-2">{t("errorKicker")}</p>
              <p className="headline text-3xl mb-2">{t("errorTitle")}</p>
              <p className="text-[var(--muted)] italic mb-4">{error}</p>
              <button
                onClick={fetchView}
                className="kicker text-[11px] border border-[var(--ink)] px-4 py-2.5 min-h-[44px] hover:bg-[var(--paper-raise)] transition-colors"
              >
                {t("tryAgain")}
              </button>
            </div>
          )}

          {!loading && !error && !edition && (
            <div className="text-center py-16 border-y-2 border-[var(--ink)] my-8">
              <p className="kicker text-[10px] text-[var(--accent)] mb-2">{t("emptyKicker")}</p>
              <p className="headline text-3xl mb-2">{t("emptyTitle")}</p>
              <p className="text-[var(--muted)] italic max-w-md mx-auto">{t("emptyBody")}</p>
            </div>
          )}

          {!loading && !error && edition && (
            <div key={`${edition.date}:${lang}:${filter ?? "all"}`} className="edition-enter">
              {!filter && edition.intro && (
                <p className="max-w-2xl mx-auto mb-8 leading-relaxed text-[15px]">
                  <span className="kicker text-[10px] text-[var(--accent)] font-bold mr-2">
                    {t("editorsDesk")}
                  </span>
                  <span className="italic text-[var(--muted)]">{edition.intro}</span>
                </p>
              )}

              {filter && (
                <p className="kicker text-[11px] text-[var(--muted)] mb-4 border-b border-[var(--rule)] pb-2">
                  {category(filter)} — {filtered.length}{" "}
                  {filtered.length === 1 ? t("dispatch") : t("dispatches")}
                </p>
              )}

              {lead && <LeadStory article={lead} />}

              {river.length > 0 ? (
                <div className="story-river md:columns-2 lg:columns-3 md:gap-8 lg:gap-10">
                  {river.map((a) => (
                    <ArticleCard key={a.id} article={a} />
                  ))}
                </div>
              ) : (
                !lead && (
                  <p className="text-center text-[var(--muted)] italic py-8">
                    {t("noSectionDispatches")}
                  </p>
                )
              )}
            </div>
          )}
        </main>

        <Footer edition={edition} issueNo={issueNo} />
      </div>
    </div>
  );
}
