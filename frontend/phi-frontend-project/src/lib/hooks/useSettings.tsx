import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type AccentTheme = "cyan" | "violet" | "emerald";
export type ColorMode = "light" | "dark" | "system";

export interface Settings {
  colorMode: ColorMode;
  accentTheme: AccentTheme;
  backendUrl: string;
  animationsEnabled: boolean;
}

const SETTINGS_KEY = "phi-guard:settings";

const DEFAULT_SETTINGS: Settings = {
  colorMode: "system",
  accentTheme: "cyan",
  backendUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
  animationsEnabled: true,
};

function loadSettings(): Settings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = window.localStorage.getItem(SETTINGS_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<Settings>) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

interface SettingsContextValue {
  settings: Settings;
  updateSettings: (patch: Partial<Settings>) => void;
  resolvedDark: boolean;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(() => loadSettings());
  const [systemPrefersDark, setSystemPrefersDark] = useState(
    () =>
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-color-scheme: dark)").matches,
  );

  useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => setSystemPrefersDark(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  }, [settings]);

  const resolvedDark =
    settings.colorMode === "dark" ||
    (settings.colorMode === "system" && systemPrefersDark);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolvedDark);
    document.documentElement.dataset.accent = settings.accentTheme;
  }, [resolvedDark, settings.accentTheme]);

  const updateSettings = (patch: Partial<Settings>) =>
    setSettings((prev) => ({ ...prev, ...patch }));

  const value = useMemo(
    () => ({ settings, updateSettings, resolvedDark }),
    [settings, resolvedDark],
  );

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used within SettingsProvider");
  return ctx;
}

export function getStoredBackendUrl(): string {
  return loadSettings().backendUrl;
}
