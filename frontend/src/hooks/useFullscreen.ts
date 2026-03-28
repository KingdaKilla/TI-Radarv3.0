/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Fullscreen Hook
 * Toggles fullscreen mode on a referenced element
 * using the Fullscreen API
 * ────────────────────────────────────────────── */

import { useState, useCallback, useEffect, type RefObject } from "react";

interface UseFullscreenReturn {
  isFullscreen: boolean;
  toggleFullscreen: () => void;
}

export function useFullscreen(ref: RefObject<HTMLElement>): UseFullscreenReturn {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Listen to fullscreen changes (also covers Escape key exit)
  useEffect(() => {
    function handleChange() {
      setIsFullscreen(document.fullscreenElement !== null);
    }

    document.addEventListener("fullscreenchange", handleChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleChange);
    };
  }, []);

  const toggleFullscreen = useCallback(() => {
    const el = ref.current;
    if (!el) return;

    if (!document.fullscreenElement) {
      el.requestFullscreen().catch((err) => {
        console.warn("Vollbildmodus konnte nicht aktiviert werden:", err);
      });
    } else {
      document.exitFullscreen().catch((err) => {
        console.warn("Vollbildmodus konnte nicht beendet werden:", err);
      });
    }
  }, [ref]);

  return { isFullscreen, toggleFullscreen };
}
