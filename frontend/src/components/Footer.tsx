import type { Edition } from "../types";
import { formatLongDate } from "../lib/format";
import { useI18n } from "../i18n";

interface Props {
  edition: Edition | null;
  issueNo: number | null;
}

export function Footer({ edition, issueNo }: Props) {
  const { lang, t } = useI18n();
  return (
    <footer className="mt-12 border-t-4 border-double border-[var(--ink)] pt-4 pb-8 text-center">
      <p className="masthead-title !text-2xl !whitespace-normal font-black mb-2">The Daily Model</p>
      {edition ? (
        <p className="kicker text-[10px] text-[var(--muted)] flex flex-wrap justify-center gap-x-3 gap-y-1">
          {issueNo != null && (
            <>
              <span>
                {t("issueNo")} {issueNo}
              </span>
              <span aria-hidden>·</span>
            </>
          )}
          <span>{formatLongDate(edition.date, lang)}</span>
          <span aria-hidden>·</span>
          <span>
            {edition.article_count} {t("dispatches")}
          </span>
          <span aria-hidden>·</span>
          <span className="border border-[var(--rule)] px-1.5 py-0.5">
            {t("setInTypeBy", { model: edition.model || "AI" })}
          </span>
        </p>
      ) : null}
      <p className="kicker text-[10px] text-[var(--muted)] mt-2">{t("footerTagline")}</p>
      <p className="kicker text-[10px] mt-2">
        <a
          href="https://github.com/mjebalidev/thedailymodel"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[var(--muted)] underline underline-offset-2 hover:text-[var(--accent)] transition-colors"
        >
          {t("viewSource")}
        </a>
      </p>
    </footer>
  );
}
