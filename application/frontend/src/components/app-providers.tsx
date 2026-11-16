"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  api,
  type CapabilitiesResponse,
  type ServiceInfo,
  type HealthResponse,
  type ReadinessResponse,
} from "../lib/api";
import { messages, type Language } from "../lib/i18n";
import {
  readPreference,
  resolveTheme,
  writePreference,
  type ThemePreference,
} from "../lib/preferences";

type CapabilityState = {
  data: CapabilitiesResponse | null;
  loading: boolean;
  error: string | null;
  info: ServiceInfo | null;
  live: HealthResponse | null;
  ready: ReadinessResponse | null;
  refresh: () => Promise<void>;
};
type AppContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  theme: ThemePreference;
  setTheme: (theme: ThemePreference) => void;
  t: <K extends keyof typeof messages.en>(key: K) => (typeof messages.en)[K];
  capabilities: CapabilityState;
};

const AppContext = createContext<AppContextValue | null>(null);

export function AppProviders({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en");
  const [theme, setThemeState] = useState<ThemePreference>("system");
  const [capabilityData, setCapabilityData] =
    useState<CapabilitiesResponse | null>(null);
  const [capabilityLoading, setCapabilityLoading] = useState(true);
  const [capabilityError, setCapabilityError] = useState<string | null>(null);
  const [info, setInfo] = useState<ServiceInfo | null>(null);
  const [live, setLive] = useState<HealthResponse | null>(null);
  const [ready, setReady] = useState<ReadinessResponse | null>(null);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setLanguageState(
        readPreference<Language>(
          localStorage,
          "bharatcrop-language",
          ["en", "hi"],
          "en",
        ),
      );
      setThemeState(
        readPreference<ThemePreference>(
          localStorage,
          "bharatcrop-theme",
          ["light", "dark", "system"],
          "system",
        ),
      );
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.lang = language;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      root.dataset.theme = resolveTheme(theme, media.matches);
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme, language]);

  const refresh = useCallback(async () => {
    setCapabilityLoading(true);
    setCapabilityError(null);
    const [capabilityResult, infoResult, liveResult, readyResult] =
      await Promise.allSettled([
        api.refreshCapabilities(),
        api.info(),
        api.live(),
        api.ready(),
      ]);
    if (capabilityResult.status === "fulfilled") {
      setCapabilityData(capabilityResult.value);
    } else {
      setCapabilityError(
        capabilityResult.reason instanceof Error
          ? capabilityResult.reason.message
          : "Service status is unavailable.",
      );
    }
    if (infoResult.status === "fulfilled") setInfo(infoResult.value);
    if (liveResult.status === "fulfilled") setLive(liveResult.value);
    if (readyResult.status === "fulfilled") setReady(readyResult.value);
    setCapabilityLoading(false);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.capabilities(),
      api.info(),
      api.live(),
      api.ready(),
    ]).then(([capabilityResult, infoResult, liveResult, readyResult]) => {
      if (!active) return;
      if (capabilityResult.status === "fulfilled") {
        setCapabilityData(capabilityResult.value);
        setCapabilityError(null);
      } else {
        setCapabilityError(
          capabilityResult.reason instanceof Error
            ? capabilityResult.reason.message
            : "Service status is unavailable.",
        );
      }
      if (infoResult.status === "fulfilled") setInfo(infoResult.value);
      if (liveResult.status === "fulfilled") setLive(liveResult.value);
      if (readyResult.status === "fulfilled") setReady(readyResult.value);
      setCapabilityLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  const setLanguage = useCallback((value: Language) => {
    setLanguageState(value);
    try {
      writePreference(localStorage, "bharatcrop-language", value);
    } catch {
      // Preference remains active for the current page when storage is unavailable.
    }
  }, []);
  const setTheme = useCallback((value: ThemePreference) => {
    setThemeState(value);
    try {
      writePreference(localStorage, "bharatcrop-theme", value);
    } catch {
      // Preference remains active for the current page when storage is unavailable.
    }
  }, []);
  const value = useMemo<AppContextValue>(
    () => ({
      language,
      setLanguage,
      theme,
      setTheme,
      t: (key) => messages[language][key],
      capabilities: {
        data: capabilityData,
        loading: capabilityLoading,
        error: capabilityError,
        info,
        live,
        ready,
        refresh,
      },
    }),
    [
      language,
      setLanguage,
      theme,
      setTheme,
      capabilityData,
      capabilityLoading,
      capabilityError,
      info,
      live,
      ready,
      refresh,
    ],
  );
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const value = useContext(AppContext);
  if (!value) throw new Error("useApp must be used within AppProviders.");
  return value;
}

export function useMessage(key: keyof typeof messages.en) {
  return useApp().t(key);
}
