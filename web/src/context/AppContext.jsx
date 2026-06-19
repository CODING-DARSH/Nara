// NARA — App Context
// Fix 3 & 4: shared "data freshness" bus so logging a meal on one page
// silently refreshes Food Graph / Recommendations on other pages without
// a full page reload and without the user noticing any jump/flicker.
import { createContext, useContext, useState, useCallback, useRef } from "react";
import { user as userApi } from "../services/api";

const AppCtx = createContext(null);

export function AppProvider({ children }) {
  // Incrementing this number is the "something changed, please refetch"
  // signal. Pages that depend on food graph / recommendations subscribe
  // via useFoodGraphVersion() and refetch in a useEffect — no reload.
  const [graphVersion, setGraphVersion] = useState(0);
  const recomputeInFlight = useRef(false);

  /**
   * Call this immediately after a meal is successfully logged.
   * It tries the synchronous recompute safety-net endpoint first
   * (food_graph_recompute.py) so the very next fetch is guaranteed
   * fresh instead of racing the Kafka enrichment pipeline. If that
   * endpoint isn't deployed yet, it falls back to a short delay + a
   * normal refetch, which still beats not refreshing at all.
   */
  const notifyMealLogged = useCallback(async () => {
    if (recomputeInFlight.current) return;
    recomputeInFlight.current = true;
    try {
      if (userApi.recomputeFoodGraph) {
        await userApi.recomputeFoodGraph().catch(() => null);
      } else {
        // Fallback: give the async pipeline a moment before bumping version
        await new Promise((r) => setTimeout(r, 1200));
      }
    } finally {
      recomputeInFlight.current = false;
      setGraphVersion((v) => v + 1);
    }
  }, []);

  const value = { graphVersion, notifyMealLogged };
  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export function useAppContext() {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("useAppContext must be used within AppProvider");
  return ctx;
}

// Convenience hook: just the version number, for components that only
// need to know "should I refetch now" without calling notifyMealLogged.
export function useFoodGraphVersion() {
  const { graphVersion } = useAppContext();
  return graphVersion;
}