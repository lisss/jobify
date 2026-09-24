"use client";

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  KeyboardEvent,
} from "react";
import type { RoleSuggestion } from "@/lib/api";

type RoleTypeaheadProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  fetchSuggestions: (query: string) => Promise<RoleSuggestion[]>;
  placeholder?: string;
  required?: boolean;
};

export function RoleTypeahead({
  label,
  value,
  onChange,
  fetchSuggestions,
  placeholder,
  required,
}: RoleTypeaheadProps) {
  const inputId = useId();
  const listId = `${inputId}-list`;
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<RoleSuggestion[]>([]);
  const [active, setActive] = useState(-1);
  const [loading, setLoading] = useState(false);

  const load = useCallback(
    async (q: string) => {
      setLoading(true);
      try {
        const next = await fetchSuggestions(q);
        setItems(next);
        setActive(next.length ? 0 : -1);
      } catch {
        setItems([]);
        setActive(-1);
      } finally {
        setLoading(false);
      }
    },
    [fetchSuggestions],
  );

  useEffect(() => {
    if (!open) return;
    const handle = window.setTimeout(() => {
      void load(value);
    }, 220);
    return () => window.clearTimeout(handle);
  }, [value, open, load]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function select(item: RoleSuggestion) {
    onChange(item.title);
    setOpen(false);
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setOpen(true);
      return;
    }
    if (!open) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (items.length ? (i + 1) % items.length : -1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) =>
        items.length ? (i - 1 + items.length) % items.length : -1,
      );
    } else if (e.key === "Enter" && active >= 0 && items[active]) {
      e.preventDefault();
      select(items[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={rootRef} className="relative block">
      <label htmlFor={inputId} className="mb-1.5 block text-sm text-[var(--muted)]">
        {label}
      </label>
      <input
        id={inputId}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        value={value}
        required={required}
        placeholder={placeholder}
        autoComplete="off"
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onKeyDown={onKeyDown}
        className="w-full rounded-xl border border-[var(--line)] bg-white px-3.5 py-2.5 text-[15px] text-[var(--ink)] outline-none transition focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
      />
      {open && (items.length > 0 || loading) && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-30 mt-1.5 max-h-72 w-full overflow-auto rounded-xl border border-[var(--line)] bg-white py-1 shadow-[0_12px_32px_rgba(15,23,22,0.08)]"
        >
          {loading && items.length === 0 && (
            <li className="px-3.5 py-2 text-sm text-[var(--muted)]">
              Searching job boards…
            </li>
          )}
          {items.map((item, index) => (
            <li
              id={`${listId}-${index}`}
              key={`${item.source}-${item.id ?? item.title}-${index}`}
              role="option"
              aria-selected={index === active}
              onMouseEnter={() => setActive(index)}
              className={`flex items-start gap-2 px-3 py-2.5 ${
                index === active ? "bg-[var(--surface-soft)]" : ""
              }`}
            >
              <button
                type="button"
                className="min-w-0 flex-1 text-left"
                onMouseDown={(e) => {
                  e.preventDefault();
                  select(item);
                }}
              >
                <span className="block text-[15px] font-medium text-[var(--ink)]">
                  {item.title}
                </span>
                <span className="mt-0.5 block text-xs text-[var(--muted)]">
                  {[item.company, item.location, item.source]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </button>
              {item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  onMouseDown={(e) => e.stopPropagation()}
                  className="shrink-0 rounded-lg px-2 py-1 text-xs font-medium text-[var(--accent)] underline decoration-[var(--line)] underline-offset-2 hover:decoration-[var(--accent)]"
                  title={`Open on ${item.source}`}
                >
                  Open
                </a>
              ) : (
                <span className="shrink-0 px-2 py-1 text-xs text-[var(--muted)]">
                  —
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
