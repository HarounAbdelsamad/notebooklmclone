import { useEffect, useState } from "react";

const PHASES = ["Sending", "Processing", "Fetching sources", "Generating", "Finalizing"];
const PHASE_INTERVAL_MS = 1600;

/**
 * Friendly animated status shown while an assistant message is streaming
 * but has not yet received its first token. Purely a frontend affordance —
 * the SSE contract only tells us `start` then `token`*, so we cycle through
 * plausible phases on a timer rather than reflecting real backend state.
 */
export function StreamingStatus() {
  const [phaseIndex, setPhaseIndex] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setPhaseIndex((i) => Math.min(i + 1, PHASES.length - 1));
    }, PHASE_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, []);

  return (
    <span className="status-pill">
      {PHASES[phaseIndex]}
      <span className="dots">
        <span />
        <span />
        <span />
      </span>
    </span>
  );
}
