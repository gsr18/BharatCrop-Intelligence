import type { Language } from "./i18n";

export type ThemePreference = "light" | "dark" | "system";

export function readPreference<T extends string>(
  storage: Pick<Storage, "getItem">,
  key: string,
  allowed: readonly T[],
  fallback: T,
): T {
  try {
    const value = storage.getItem(key);
    return allowed.includes(value as T) ? (value as T) : fallback;
  } catch {
    return fallback;
  }
}

export function writePreference(
  storage: Pick<Storage, "setItem">,
  key: string,
  value: Language | ThemePreference,
) {
  storage.setItem(key, value);
}

export function resolveTheme(preference: ThemePreference, systemDark: boolean) {
  return preference === "system" ? (systemDark ? "dark" : "light") : preference;
}
