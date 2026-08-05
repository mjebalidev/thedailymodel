import { useI18n } from "../i18n";

export function Skeleton() {
  const { t } = useI18n();
  return (
    <div role="status" aria-live="polite" aria-busy="true">
      <p className="text-center kicker text-[11px] text-[var(--muted)] mb-6">{t("settingType")}</p>

      {/* Lead ghost */}
      <div className="pb-6 mb-6 border-b-2 border-[var(--ink)]">
        <div className="ink-ghost h-3 w-24 mb-3" />
        <div className="ink-ghost h-9 w-4/5 mb-2" />
        <div className="ink-ghost h-9 w-3/5 mb-4" />
        {[...Array(6)].map((_, i) => (
          <div key={i} className={`ink-ghost h-3.5 mb-2 ${i === 5 ? "w-2/3" : "w-full"}`} />
        ))}
      </div>

      {/* River ghosts */}
      <div className="md:columns-2 lg:columns-3 md:gap-8 lg:gap-10">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="break-inside-avoid mb-6 pb-6 border-b border-[var(--rule)]">
            <div className="ink-ghost h-3 w-20 mb-3" />
            <div className="ink-ghost h-6 w-full mb-2" />
            <div className="ink-ghost h-6 w-2/3 mb-3" />
            {[...Array(4)].map((_, j) => (
              <div key={j} className={`ink-ghost h-3 mb-2 ${j === 3 ? "w-1/2" : "w-full"}`} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
