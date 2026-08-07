import { useEffect, useRef, useState } from "react";
import { formatLongDate } from "../lib/format";
import type { Theme } from "../hooks/useTheme";
import { useI18n } from "../i18n";
import { ThemeToggle } from "./ThemeToggle";
import { LanguageSwitcher } from "./LanguageSwitcher";

interface Props {
  date: string | null;
  subtitle: string;
  model: string;
  theme: Theme;
  onCycleTheme: () => void;
}

export function Masthead({ date, subtitle, model, theme, onCycleTheme }: Props) {
  const { lang, t } = useI18n();
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [condensed, setCondensed] = useState(false);
  const isDraft = model === "mock";

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const ob = new IntersectionObserver(([entry]) => setCondensed(!entry.isIntersecting), {
      rootMargin: "-8px 0px 0px 0px",
    });
    ob.observe(el);
    return () => ob.disconnect();
  }, []);

  return (
    <>
      {/* Condensed sticky nameplate — slides in once the full masthead scrolls away */}
      <div
        aria-hidden={!condensed}
        className={`fixed inset-x-0 top-0 z-40 bg-[var(--paper)] border-b-2 border-[var(--ink)] px-4 flex items-center justify-between transition-transform duration-200 ${
          condensed ? "translate-y-0" : "-translate-y-full"
        }`}
        style={{ paddingTop: "max(0.5rem, env(safe-area-inset-top))", paddingBottom: "0.5rem" }}
      >
        <span className="masthead-title !text-xl font-black">The Daily Model</span>
        <div className="flex items-center gap-2">
          <span className="hidden md:block kicker text-[10px] text-[var(--muted)]">
            {date ? formatLongDate(date, lang) : ""}
          </span>
          <LanguageSwitcher />
          <ThemeToggle theme={theme} onCycle={onCycleTheme} />
        </div>
      </div>

      <header className="border-b-4 border-double border-[var(--ink)] pb-2 mb-4 sm:pb-3 sm:mb-6">
        <div className="flex items-center justify-between gap-2 text-xs kicker text-[var(--muted)] pb-2">
          <span className="truncate max-w-[40vw]">{date ? formatLongDate(date, lang) : "—"}</span>
          <span className="hidden lg:block">{t("autonomousDesk")}</span>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <ThemeToggle theme={theme} onCycle={onCycleTheme} />
          </div>
        </div>

        <div className="relative border-y border-[var(--rule)] py-3 text-center">
          {isDraft && (
            <span className="absolute right-1 top-1 sm:right-4 sm:top-3 -rotate-6 kicker text-[10px] font-bold text-[var(--accent)] border border-[var(--accent)] px-1.5 py-0.5">
              {t("draft")}
            </span>
          )}
          <h1 className="masthead-title font-black">The Daily Model</h1>
          {subtitle && (
            <p className="mt-1 text-sm sm:text-base italic text-[var(--muted)]">{subtitle}</p>
          )}
        </div>

        <div className="hidden sm:flex items-center justify-between pt-2">
          <span className="kicker text-[10px] text-[var(--muted)]">{t("tagline")}</span>
          <span className="kicker text-[10px] text-[var(--muted)]">{t("publishedDaily")}</span>
        </div>
      </header>

      <div ref={sentinelRef} aria-hidden />
    </>
  );
}
