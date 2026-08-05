import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark" | "sepia";

const KEY = "tdm-theme";
const ORDER: Theme[] = ["light", "dark", "sepia"];

export const THEME_LABEL: Record<Theme, string> = {
  light: "Daylight Ed.",
  dark: "Evening Ed.",
  sepia: "Newsprint Ed.",
};

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem(KEY) as Theme | null;
    if (saved && ORDER.includes(saved)) return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      /* ignore */
    }
    // Keep the mobile browser chrome tinted to the current paper color.
    const paper = getComputedStyle(document.documentElement).getPropertyValue("--paper").trim();
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", paper || "#f7f4ec");
  }, [theme]);

  const cycle = useCallback(() => {
    setTheme((t) => ORDER[(ORDER.indexOf(t) + 1) % ORDER.length]);
  }, []);

  return { theme, cycle };
}
