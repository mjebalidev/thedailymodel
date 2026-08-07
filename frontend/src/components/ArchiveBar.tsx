import { useEffect, useMemo, useRef } from "react";
import type { EditionSummary } from "../types";
import { formatMonthYear, formatShortDate } from "../lib/format";
import { useI18n } from "../i18n";

interface Props {
  editions: EditionSummary[];
  currentDate: string | null;
  onSelect: (date: string) => void;
}

// Editions shown as individual tabs; the rest collapse into a per-month picker
// so the bar stays usable once the archive spans months.
const RECENT_TABS = 10;

export function ArchiveBar({ editions, currentDate, onSelect }: Props) {
  const { lang, t } = useI18n();
  const activeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [currentDate]);

  // editions arrive newest-first from the API.
  const recent = editions.slice(0, RECENT_TABS);
  const older = editions.slice(RECENT_TABS);

  const olderByMonth = useMemo(() => {
    const groups = new Map<string, EditionSummary[]>();
    for (const e of older) {
      const month = e.date.slice(0, 7); // "YYYY-MM"
      const group = groups.get(month);
      if (group) group.push(e);
      else groups.set(month, [e]);
    }
    return [...groups.entries()];
  }, [older]);

  const currentIsOlder = older.some((e) => e.date === currentDate);

  if (editions.length <= 1) return null;

  return (
    <nav aria-label="Back issues" className="mb-6 border-b border-[var(--rule)] overflow-x-auto archive-scroll">
      <div className="flex items-center gap-1 whitespace-nowrap">
        <span className="kicker text-[11px] text-[var(--muted)] pr-1">{t("backIssues")}</span>
        {recent.map((e) => {
          const isActive = e.date === currentDate;
          return (
            <button
              key={e.id}
              ref={isActive ? activeRef : undefined}
              onClick={() => onSelect(e.date)}
              aria-current={isActive ? "date" : undefined}
              className={`kicker text-[11px] px-3 py-2.5 min-h-[44px] border-b-2 transition-colors ${
                isActive
                  ? "border-[var(--accent)] text-[var(--accent)] font-bold"
                  : "border-transparent text-[var(--ink)] hover:text-[var(--accent)]"
              }`}
            >
              {formatShortDate(e.date, lang)}
            </button>
          );
        })}
        {older.length > 0 && (
          <select
            value={currentIsOlder && currentDate ? currentDate : ""}
            onChange={(ev) => ev.target.value && onSelect(ev.target.value)}
            aria-label={t("olderIssues")}
            className={`kicker text-[11px] px-2 py-2.5 min-h-[44px] border-b-2 bg-transparent cursor-pointer transition-colors ${
              currentIsOlder
                ? "border-[var(--accent)] text-[var(--accent)] font-bold"
                : "border-transparent text-[var(--ink)] hover:text-[var(--accent)]"
            }`}
          >
            <option value="" disabled>
              {t("olderIssues")} ({older.length}) ▾
            </option>
            {olderByMonth.map(([month, items]) => (
              <optgroup key={month} label={formatMonthYear(month, lang)}>
                {items.map((e) => (
                  <option key={e.id} value={e.date}>
                    {formatShortDate(e.date, lang)}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        )}
      </div>
    </nav>
  );
}
