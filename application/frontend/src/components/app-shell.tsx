"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { createPortal } from "react-dom";
import { useApp } from "./app-providers";
import { navItems, type MessageKey } from "../lib/i18n";
import type { ThemePreference } from "../lib/preferences";
import type {
  KeyboardEvent as ReactKeyboardEvent,
  ReactNode,
  Ref,
} from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { AiAssistantIcon } from "./icons";

const PRIMARY_HREFS = ["/yield", "/crops", "/weather", "/risk"] as const;
const SECONDARY_HREFS = [
  "/explainability",
  "/insights",
  "/research",
  "/model-development",
] as const;

function BrandMark() {
  return (
    <svg
      aria-hidden="true"
      className="brand-mark"
      viewBox="0 0 40 40"
      fill="none"
    >
      <path
        d="M7 31.5C10.7 22.7 19.4 12.8 33 8.5c-1.6 12.2-8.8 22.8-20.8 23.2"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <path
        d="M8 32c5.8-7.3 11.6-11.4 19.1-15"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M8 32h24"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function DesktopNavigation() {
  const pathname = usePathname();
  const { t } = useApp();
  const primaryNav = navItems.filter((item) =>
    (PRIMARY_HREFS as readonly string[]).includes(item.href),
  );
  return (
    <nav className="glass-nav" aria-label={t("primaryNavigation")}>
      {primaryNav.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            className="nav-link"
            href={item.href}
            key={item.href}
            aria-current={active ? "page" : undefined}
          >
            {t(item.key)}
          </Link>
        );
      })}
    </nav>
  );
}

function MoreMenu() {
  const pathname = usePathname();
  const { t } = useApp();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Array<HTMLAnchorElement | null>>([]);

  const secondaryNav = navItems.filter((item) =>
    (SECONDARY_HREFS as readonly string[]).includes(item.href),
  );

  useEffect(() => {
    if (!open) return;
    const onDocMouseDown = (event: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open]);

  useEffect(() => {
    if (open) {
      itemRefs.current[0]?.focus();
    }
  }, [open]);

  const setItemRef = (index: number) => (el: HTMLAnchorElement | null) => {
    itemRefs.current[index] = el;
  };

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
      return;
    }
    if (event.key === "Tab") {
      setOpen(false);
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const list = itemRefs.current.filter(Boolean) as HTMLAnchorElement[];
      if (!list.length) return;
      const active = document.activeElement as HTMLElement | null;
      const idx = list.findIndex((el) => el === active);
      const next =
        event.key === "ArrowDown"
          ? (idx + 1 + list.length) % list.length
          : (idx - 1 + list.length) % list.length;
      list[next]?.focus();
    }
  };

  const activeInMore = secondaryNav.some((item) => pathname === item.href);

  return (
    <div className="nav-more" ref={wrapRef} onKeyDown={handleKeyDown}>
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={t("more")}
        className={`icon-control nav-more-button${
          activeInMore ? " is-active" : ""
        }`}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="nav-more-label">{t("more")}</span>
        <span aria-hidden="true" className="nav-more-caret">
          ⌄
        </span>
      </button>
      {open && (
        <div className="nav-more-menu" role="menu">
          {secondaryNav.map((item, i) => (
            <Link
              key={item.href}
              role="menuitem"
              className="nav-more-link"
              href={item.href}
              aria-current={pathname === item.href ? "page" : undefined}
              onClick={() => setOpen(false)}
              ref={setItemRef(i) as Ref<HTMLAnchorElement>}
            >
              {t(item.key)}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function MobileNavigation() {
  const pathname = usePathname();
  const { t } = useApp();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen]);

  const overlay =
    typeof document === "undefined"
      ? null
      : createPortal(
          <nav
            className="mobile-nav-overlay"
            aria-label={t("primaryNavigation")}
          >
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  className="mobile-nav-link"
                  href={item.href}
                  key={item.href}
                  aria-current={active ? "page" : undefined}
                  onClick={() => setIsOpen(false)}
                >
                  {t(item.key)}
                </Link>
              );
            })}
          </nav>,
          document.body,
        );

  return (
    <>
      <button
        className="mobile-menu-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={t("toggleMenu")}
        aria-expanded={isOpen}
      >
        <span className="hamburger" />
      </button>
      {isOpen ? overlay : null}
    </>
  );
}

function ThemeToggle() {
  const { theme, setTheme, t } = useApp();
  const cycle: ThemePreference[] = ["system", "light", "dark"];
  const glyphs: Record<ThemePreference, string> = {
    system: "◐",
    light: "☀",
    dark: "☾",
  };
  const label: Record<ThemePreference, MessageKey> = {
    system: "system",
    light: "light",
    dark: "dark",
  };
  return (
    <button
      type="button"
      className="icon-control theme-toggle"
      aria-label={`${t("theme")}: ${t(label[theme])}`}
      title={`${t("theme")}: ${t(label[theme])}`}
      onClick={() => {
        const idx = cycle.indexOf(theme);
        setTheme(cycle[(idx + 1) % cycle.length]);
      }}
    >
      <span aria-hidden="true">{glyphs[theme]}</span>
    </button>
  );
}

function LanguageToggle() {
  const { language, setLanguage, t } = useApp();
  return (
    <button
      type="button"
      className="icon-control lang-toggle"
      aria-label={`${t("language")}: ${language.toUpperCase()}`}
      title={t("language")}
      onClick={() => setLanguage(language === "en" ? "hi" : "en")}
    >
      <span>{language === "en" ? "EN" : "हि"}</span>
    </button>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useApp();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const searchableItems = useMemo(
    () =>
      navItems.map((item) => ({
        href: item.href,
        label: t(item.key),
        detail:
          item.href === "/model-development"
            ? t("learningGuide")
            : t("moduleDetail"),
      })),
    [t],
  );

  const filteredItems = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return searchableItems;
    return searchableItems.filter((item) =>
      `${item.label} ${item.detail}`.toLowerCase().includes(q),
    );
  }, [searchableItems, searchQuery]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen((value) => !value);
      } else if (event.key === "Escape") {
        setSearchOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="app-frame">
      <header className="glass-header">
        <Link
          className="brand"
          href="/"
          aria-label="BharatCrop Intelligence home"
        >
          <BrandMark />
          <span className="brand-copy">
            <strong>BharatCrop</strong>
            <span>Intelligence</span>
          </span>
        </Link>

        <DesktopNavigation />

        <div className="header-actions">
          <ThemeToggle />
          <button
            type="button"
            className="icon-control search-trigger"
            aria-label={`${t("searchPlaceholder")} (Ctrl+K)`}
            title={`${t("searchPlaceholder")} (Ctrl+K)`}
            onClick={() => setSearchOpen(true)}
          >
            <span aria-hidden="true">⌕</span>
          </button>
          <LanguageToggle />
          <Link
            href="/assistant"
            className="icon-control assistant-trigger"
            aria-label={t("assistant")}
            title={t("assistant")}
          >
            <AiAssistantIcon size={18} />
          </Link>
          <MoreMenu />
          <MobileNavigation />
        </div>
      </header>

      <main className="page-content">
        {children}
        <footer className="app-footer">
          <Link className="footer-brand" href="/">
            BharatCrop <span>Intelligence</span>
          </Link>
          <nav aria-label="Footer navigation">
            <Link href="/research">{t("research")}</Link>
            <Link href="/model-development">{t("modelDevelopment")}</Link>
            <Link href="/yield">{t("yield")}</Link>
          </nav>
          <p>{t("appFooterTagline")}</p>
        </footer>
      </main>

      {searchOpen && (
        <div
          className="command-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setSearchOpen(false);
          }}
        >
          <section
            aria-label={t("searchPlaceholder")}
            aria-modal="true"
            className="command-dialog"
            role="dialog"
          >
            <div className="command-input-row">
              <span aria-hidden="true">⌕</span>
              <input
                autoFocus
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder={t("searchPlaceholder")}
                value={searchQuery}
                aria-label={t("searchPlaceholder")}
              />
              <button type="button" onClick={() => setSearchOpen(false)}>
                Esc
              </button>
            </div>
            <p className="command-caption">{t("searchCaption")}</p>
            <div className="command-results">
              {filteredItems.length ? (
                filteredItems.map((item) => (
                  <Link
                    href={item.href}
                    key={`${item.href}-${item.label}`}
                    onClick={() => {
                      setSearchOpen(false);
                      setSearchQuery("");
                    }}
                  >
                    <span>{item.label}</span>
                    <small>{item.detail}</small>
                    <span aria-hidden="true">↗</span>
                  </Link>
                ))
              ) : (
                <p className="command-empty">{t("searchEmpty")}</p>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
