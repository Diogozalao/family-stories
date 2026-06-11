import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Draft of the "Generate story" wizard, persisted to localStorage.
 *
 * The wizard used to keep its state in component-local ``useState``, so
 * navigating away (e.g. to Projects) and back wiped everything the user
 * had filled in. Mirroring it into a persisted Zustand store keeps the
 * draft alive across navigation and reloads; it's cleared explicitly only
 * after a story is successfully generated (``reset()``).
 */
export type GenStep = 1 | 2 | 3 | 4;

interface GenerateDraft {
  step: GenStep;
  eventType: string;
  title: string;
  query: string;
  customTone: string;
  customStructure: string;
  selectedIds: number[];
  mode: "sync" | "background";
  patch: (partial: Partial<GenerateDraftFields>) => void;
  reset: () => void;
}

type GenerateDraftFields = Omit<GenerateDraft, "patch" | "reset">;

const INITIAL: GenerateDraftFields = {
  step: 1,
  eventType: "default",
  title: "",
  query: "",
  customTone: "",
  customStructure: "",
  selectedIds: [],
  mode: "background",
};

export const useGenerateDraft = create<GenerateDraft>()(
  persist(
    (set) => ({
      ...INITIAL,
      patch: (partial) => set(partial),
      reset: () => set(INITIAL),
    }),
    { name: "lm-generate-draft" },
  ),
);
