import { useEffect, useRef } from "react";
import type { EditionSummary } from "../types";
import { formatShortDate } from "../lib/format";
import { useI18n } from "../i18n";

interface Props {
  editions: EditionSummary[];
  currentDate: string | null;
  onSelect: (date: string) => void;
}

export function ArchiveBar({ editions, currentDate, onSelect }: Props) {
  const { t } = useI18n();
  const activeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [currentDate]);

  if (editions.length <= 1) return null;

  return (
    <nav aria-label="Back issues" className="mb-6 border-b border-[var(--rule)] overflow-x-auto archive-scroll">
      <div className="flex items-center gap-1 whitespace-nowrap">
        <span className="kicker text-[11px] text-[var(--muted)] pr-1">{t("backIssues")}</span>
        {editions.map((e) => {
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
              {formatShortDate(e.date)}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
