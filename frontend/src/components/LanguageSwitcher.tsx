import { LANGS, useI18n } from "../i18n";

export function LanguageSwitcher() {
  const { lang, setLang, t } = useI18n();
  return (
    <div className="flex items-center border border-[var(--rule)]" role="group" aria-label={t("switchLanguage")}>
      {LANGS.map((l, i) => (
        <button
          key={l}
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          className={`kicker text-[10px] px-2 py-2 min-h-[44px] sm:min-h-0 transition-colors ${
            i > 0 ? "border-l border-[var(--rule)]" : ""
          } ${
            lang === l
              ? "bg-[var(--ink)] text-[var(--paper)] font-bold"
              : "text-[var(--muted)] hover:text-[var(--ink)]"
          }`}
        >
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
