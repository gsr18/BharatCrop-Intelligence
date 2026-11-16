"use client";

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

type Option = { value: string; label?: string };

type Props = {
  id: string;
  label: string;
  value: string;
  options: readonly (string | Option)[];
  placeholder?: string;
  emptyMessage?: string;
  disabled?: boolean;
  required?: boolean;
  helpText?: string;
  onChange: (value: string) => void;
};

function normalise(option: string | Option): Option {
  return typeof option === "string" ? { value: option, label: option } : option;
}

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

export function SearchableSelect({
  id,
  label,
  value,
  options,
  placeholder = "Select an option",
  emptyMessage = "No matches found.",
  disabled,
  required,
  helpText,
  onChange,
}: Props) {
  const listboxId = `${id}-listbox`;
  const uid = useId();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const normalised = useMemo(() => options.map(normalise), [options]);
  const filtered = useMemo(() => {
    if (!query.trim()) return normalised;
    const needle = query.trim().toLocaleLowerCase();
    return normalised.filter((option) =>
      (option.label ?? option.value).toLocaleLowerCase().includes(needle),
    );
  }, [normalised, query]);

  const activeIndex = filtered.length
    ? Math.min(highlightIndex, filtered.length - 1)
    : 0;

  // Adjust local query state when the controlled `value` prop changes without
  // an effect (React's recommended render-phase state adjustment pattern).
  const [prevValue, setPrevValue] = useState(value);
  if (prevValue !== value) {
    setPrevValue(value);
    setQuery("");
  }

  useEffect(() => {
    if (!open) return;
    function onDocClick(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  function selectOption(option: Option) {
    onChange(option.value);
    setQuery("");
    setOpen(false);
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
        selectOption(filtered[activeIndex]);
      }
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  const selectedLabel =
    normalised.find((option) => option.value === value)?.label ?? "";

  return (
    <div className="searchable-combobox" ref={rootRef}>
      <label htmlFor={id}>{label}</label>
      <div className="combobox-input-wrapper">
        <input
          id={id}
          ref={inputRef}
          role="combobox"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-labelledby={`${id}-label`}
          aria-activedescendant={
            open && filtered[activeIndex]
              ? `${id}-option-${uid}-${activeIndex}`
              : undefined
          }
          autoComplete="off"
          disabled={disabled}
          required={required}
          placeholder={selectedLabel && !query ? selectedLabel : placeholder}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
            setHighlightIndex(0);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
        />
        {value && (
          <button
            type="button"
            className="clear-button"
            aria-label={`Clear ${label}`}
            onClick={() => {
              onChange("");
              setQuery("");
              setOpen(false);
              inputRef.current?.focus();
            }}
          >
            ×
          </button>
        )}
      </div>
      <span id={`${id}-label`} className="sr-only">
        {label}
      </span>
      {helpText ? <small className="form-help">{helpText}</small> : null}
      {open ? (
        <ul
          id={listboxId}
          role="listbox"
          aria-label={label}
          className="combobox-list"
        >
          {filtered.length ? (
            filtered.map((option, index) => (
              <li
                key={option.value}
                id={`${id}-option-${uid}-${index}`}
                role="option"
                aria-selected={option.value === value}
                className={`combobox-option${
                  index === activeIndex ? " highlighted" : ""
                }${option.value === value ? " selected" : ""}`}
                onMouseEnter={() => setHighlightIndex(index)}
                onClick={() => selectOption(option)}
              >
                {highlight(option.label ?? option.value, query)}
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
