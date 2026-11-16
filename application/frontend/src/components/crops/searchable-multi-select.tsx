"use client";

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

type Props = {
  id: string;
  label: string;
  values: string[];
  options: readonly string[];
  placeholder?: string;
  emptyMessage?: string;
  removeLabel?: string;
  disabled?: boolean;
  helpText?: string;
  onChange: (values: string[]) => void;
};

function highlight(label: string, query: string) {
  if (!query) return label;
  const index = label.toLocaleLowerCase().indexOf(query.toLocaleLowerCase());
  if (index === -1) return label;
  return (
    <>
      {label.slice(0, index)}
      <span className="highlight-text">
        {label.slice(index, index + query.length)}
      </span>
      {label.slice(index + query.length)}
    </>
  );
}

export function SearchableMultiSelect({
  id,
  label,
  values,
  options,
  placeholder = "Search crops…",
  emptyMessage = "No matches found.",
  removeLabel = "Remove",
  disabled,
  helpText,
  onChange,
}: Props) {
  const uid = useId();
  const listboxId = `${id}-listbox`;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const filtered = useMemo(() => {
    const available = options.filter((option) => !values.includes(option));
    if (!query.trim()) return available;
    const needle = query.trim().toLocaleLowerCase();
    return available.filter((option) =>
      option.toLocaleLowerCase().includes(needle),
    );
  }, [options, query, values]);

  const activeIndex = filtered.length
    ? Math.min(highlightIndex, filtered.length - 1)
    : 0;

  useEffect(() => {
    if (!open) return;
    function onDocClick(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  function toggle(option: string) {
    if (values.includes(option)) {
      onChange(values.filter((value) => value !== option));
    } else {
      onChange([...values, option]);
    }
    setQuery("");
    inputRef.current?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (disabled) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setHighlightIndex(Math.min(activeIndex + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightIndex(Math.max(activeIndex - 1, 0));
    } else if (event.key === "Enter") {
      if (open && filtered[activeIndex]) {
        event.preventDefault();
        toggle(filtered[activeIndex]);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
    } else if (event.key === "Backspace" && !query && values.length) {
      onChange(values.slice(0, -1));
    }
  }

  return (
    <div className="searchable-combobox crop-multi-select" ref={rootRef}>
      <label htmlFor={id}>{label}</label>
      {values.length ? (
        <ul className="chip-row" aria-label={`${label} selected`}>
          {values.map((value) => (
            <li key={value} className="chip">
              <span>{value}</span>
              <button
                type="button"
                aria-label={`${removeLabel} ${value}`}
                onClick={() =>
                  onChange(values.filter((entry) => entry !== value))
                }
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="combobox-input-wrapper">
        <input
          id={id}
          ref={inputRef}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={
            open && filtered[activeIndex]
              ? `${id}-option-${uid}-${activeIndex}`
              : undefined
          }
          autoComplete="off"
          disabled={disabled}
          placeholder={values.length ? "" : placeholder}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
            setHighlightIndex(0);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
        />
      </div>
      {helpText ? <small className="form-help">{helpText}</small> : null}
      {open ? (
        <ul id={listboxId} role="listbox" aria-label={label} className="combobox-list">
          {filtered.length ? (
            filtered.map((option, index) => (
              <li
                key={option}
                id={`${id}-option-${uid}-${index}`}
                role="option"
                aria-selected={false}
                className={`combobox-option${
                  index === activeIndex ? " highlighted" : ""
                }`}
                onMouseEnter={() => setHighlightIndex(index)}
                onClick={() => toggle(option)}
              >
                {highlight(option, query)}
              </li>
            ))
          ) : (
            <li className="combobox-option no-results" role="option" aria-disabled>
              {emptyMessage}
            </li>
          )}
        </ul>
      ) : null}
    </div>
  );
}
