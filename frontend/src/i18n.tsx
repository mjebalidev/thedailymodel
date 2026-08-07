import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

export type Lang = "en" | "fr" | "de";
export const LANGS: Lang[] = ["en", "fr", "de"];

type Vars = Record<string, string | number>;

const DICT: Record<Lang, Record<string, string>> = {
  en: {
    tagline: "All the intelligence that's fit to print",
    publishedDaily: "Published daily",
    autonomousDesk: "Autonomous AI Desk",
    draft: "Draft",
    defaultSubtitle: "A daily newspaper written by an AI research desk",
    backIssues: "Back issues:",
    olderIssues: "Older issues",
    allSections: "All",
    sources: "Sources:",
    starEdition: "★ Star Edition",
    editorsDesk: "From the Editor's Desk —",
    noSectionDispatches: "No dispatches in this section today.",
    settingType: "Setting type…",
    emptyKicker: "Notice to Readers",
    emptyTitle: "No Edition on the Stands",
    emptyBody:
      "The presses have not yet run. Today's edition will appear here as soon as it is set in type.",
    errorKicker: "Stop the Presses",
    errorTitle: "The Edition Could Not Be Fetched",
    tryAgain: "Try Again",
    skipLink: "Skip to today's edition",
    footerTagline: "Written, edited & typeset by an autonomous research desk · Published daily",
    issueNo: "No.",
    dispatch: "dispatch",
    dispatches: "dispatches",
    setInTypeBy: "Set in type by {model}",
    importanceAria: "Importance {n} of 5",
    switchLanguage: "Language",
  },
  fr: {
    tagline: "Toute l'intelligence digne d'être imprimée",
    publishedDaily: "Publié chaque jour",
    autonomousDesk: "Rédaction IA autonome",
    draft: "Brouillon",
    defaultSubtitle: "Un quotidien rédigé par une rédaction IA",
    backIssues: "Archives :",
    olderIssues: "Éditions antérieures",
    allSections: "Tout",
    sources: "Sources :",
    starEdition: "★ Édition spéciale",
    editorsDesk: "Le mot de la rédaction —",
    noSectionDispatches: "Aucune dépêche dans cette rubrique aujourd'hui.",
    settingType: "Composition en cours…",
    emptyKicker: "Avis aux lecteurs",
    emptyTitle: "Aucune édition en kiosque",
    emptyBody:
      "Les presses n'ont pas encore tourné. L'édition du jour paraîtra ici dès qu'elle sera composée.",
    errorKicker: "Arrêtez les presses",
    errorTitle: "Impossible de charger l'édition",
    tryAgain: "Réessayer",
    skipLink: "Aller à l'édition du jour",
    footerTagline: "Écrit, édité et composé par une rédaction autonome · Publié chaque jour",
    issueNo: "N°",
    dispatch: "dépêche",
    dispatches: "dépêches",
    setInTypeBy: "Composé par {model}",
    importanceAria: "Importance {n} sur 5",
    switchLanguage: "Langue",
  },
  de: {
    tagline: "Alle Intelligenz, die es wert ist, gedruckt zu werden",
    publishedDaily: "Täglich erscheinend",
    autonomousDesk: "Autonome KI-Redaktion",
    draft: "Entwurf",
    defaultSubtitle: "Eine Tageszeitung von einer KI-Redaktion",
    backIssues: "Ausgaben:",
    olderIssues: "Ältere Ausgaben",
    allSections: "Alle",
    sources: "Quellen:",
    starEdition: "★ Sonderausgabe",
    editorsDesk: "Aus der Redaktion —",
    noSectionDispatches: "Heute keine Meldungen in dieser Rubrik.",
    settingType: "Satz wird gesetzt…",
    emptyKicker: "Hinweis an die Leser",
    emptyTitle: "Keine Ausgabe am Kiosk",
    emptyBody:
      "Die Pressen laufen noch nicht. Die heutige Ausgabe erscheint hier, sobald sie gesetzt ist.",
    errorKicker: "Stoppt die Pressen",
    errorTitle: "Die Ausgabe konnte nicht geladen werden",
    tryAgain: "Erneut versuchen",
    skipLink: "Zur heutigen Ausgabe springen",
    footerTagline: "Geschrieben, redigiert & gesetzt von einer autonomen Redaktion · Täglich",
    issueNo: "Nr.",
    dispatch: "Meldung",
    dispatches: "Meldungen",
    setInTypeBy: "Gesetzt von {model}",
    importanceAria: "Wichtigkeit {n} von 5",
    switchLanguage: "Sprache",
  },
};

// Canonical (English) category -> localized label.
const CATEGORY: Record<Lang, Record<string, string>> = {
  en: {
    Research: "Research",
    Products: "Products",
    Business: "Business",
    Policy: "Policy",
    Tools: "Tools",
    Society: "Society",
  },
  fr: {
    Research: "Recherche",
    Products: "Produits",
    Business: "Affaires",
    Policy: "Politique",
    Tools: "Outils",
    Society: "Société",
  },
  de: {
    Research: "Forschung",
    Products: "Produkte",
    Business: "Wirtschaft",
    Policy: "Politik",
    Tools: "Werkzeuge",
    Society: "Gesellschaft",
  },
};

const KEY = "tdm-lang";

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(KEY) as Lang | null;
    if (saved && LANGS.includes(saved)) return saved;
    const nav = navigator.language.slice(0, 2).toLowerCase() as Lang;
    if (LANGS.includes(nav)) return nav;
  } catch {
    /* ignore */
  }
  return "en";
}

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: keyof (typeof DICT)["en"], vars?: Vars) => string;
  category: (canonical: string) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(KEY, lang);
    } catch {
      /* ignore */
    }
  }, [lang]);

  const t = useCallback(
    (key: keyof (typeof DICT)["en"], vars?: Vars) => {
      let s = DICT[lang][key] ?? DICT.en[key] ?? String(key);
      if (vars) for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, String(v));
      return s;
    },
    [lang],
  );

  const category = useCallback(
    (c: string) => CATEGORY[lang][c] ?? c,
    [lang],
  );

  const value = useMemo(
    () => ({ lang, setLang: setLangState, t, category }),
    [lang, t, category],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
