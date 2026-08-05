import type { Theme } from "../hooks/useTheme";
import { THEME_LABEL } from "../hooks/useTheme";

interface Props {
  theme: Theme;
  onCycle: () => void;
}

export function ThemeToggle({ theme, onCycle }: Props) {
  return (
    <button
      onClick={onCycle}
      aria-label={`Switch edition style (current: ${THEME_LABEL[theme]})`}
      className="kicker text-[10px] px-2 py-2 min-h-[44px] sm:min-h-0 border border-[var(--rule)] hover:border-[var(--ink)] transition-colors"
    >
      {THEME_LABEL[theme]}
    </button>
  );
}
