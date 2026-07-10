import { create } from "zustand";
import type { Citation } from "../api/types";

/** Lightweight UI state: the source/citation drawer selection. */
interface UiState {
  activeCitation: Citation | null;
  setActiveCitation: (c: Citation | null) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeCitation: null,
  setActiveCitation: (c) => set({ activeCitation: c }),
}));
