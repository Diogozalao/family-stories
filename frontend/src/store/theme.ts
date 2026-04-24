import { create } from "zustand";

export type ThemeMode = "light" | "dark" | "system";

interface ThemeState {
  mode: ThemeMode;
  setMode: (m: ThemeMode) => void;
  resolved: "light" | "dark";
  refreshResolved: () => void;
}

function resolve(mode: ThemeMode): "light" | "dark" {
  if (mode === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return mode;
}

function apply(resolved: "light" | "dark") {
  document.documentElement.classList.toggle("dark", resolved === "dark");
  try { localStorage.setItem("lm-theme", resolved); } catch { /* noop */ }
}

const initialStored = (localStorage.getItem("lm-theme-mode") as ThemeMode | null) ?? "system";
const initialResolved = resolve(initialStored);
apply(initialResolved);

export const useThemeStore = create<ThemeState>()((set, get) => {
  // Keep the resolved theme in sync when the OS flips between light and dark.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (get().mode === "system") get().refreshResolved();
  });

  return {
    mode: initialStored,
    resolved: initialResolved,
    setMode: (m) => {
      try { localStorage.setItem("lm-theme-mode", m); } catch { /* noop */ }
      const r = resolve(m);
      apply(r);
      set({ mode: m, resolved: r });
    },
    refreshResolved: () => {
      const r = resolve(get().mode);
      apply(r);
      set({ resolved: r });
    },
  };
});
