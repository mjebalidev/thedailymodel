import { useI18n } from "../i18n";

export const CATEGORIES = [
  "Research",
  "Products",
  "Business",
  "Policy",
  "Tools",
  "Society",
] as const;

interface Props {
  present: Set<string>; // categories that actually appear in this edition
  active: string | null; // null = "All"
  onSelect: (category: string | null) => void;
}

export function CategoryNav({ present, active, onSelect }: Props) {
  const { t, category } = useI18n();
  const items: (string | null)[] = [null, ...CATEGORIES];

  return (
    <nav
      aria-label="Sections"
      className="border-y-2 border-[var(--ink)] mb-4 overflow-x-auto archive-scroll"
    >
      <ul className="flex justify-start sm:justify-center whitespace-nowrap">
        {items.map((cat) => {
          const label = cat === null ? t("allSections") : category(cat);
          const isActive = active === cat;
          const disabled = cat !== null && !present.has(cat);
          return (
            <li key={cat ?? "all"}>
              <button
                onClick={() => !disabled && onSelect(cat)}
                aria-pressed={isActive}
                disabled={disabled}
                className={`kicker text-[11px] px-3 sm:px-4 py-3 min-h-[44px] transition-colors ${
                  isActive
                    ? "text-[var(--accent)] font-bold"
                    : disabled
                      ? "text-[var(--muted)] opacity-40 cursor-default"
                      : "hover:text-[var(--accent)]"
                }`}
              >
                {label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
