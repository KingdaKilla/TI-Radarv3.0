"use client";

/* ──────────────────────────────────────────────
 * TI-Radar v3 -- Cluster Carousel
 * Infinite horizontal slider: always shows 3 cards.
 * Seamless wrap-around via clone slides + direct DOM
 * reflow trick (zero-frame jump, no flicker).
 * ────────────────────────────────────────────── */

import { useCallback, useRef, useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";
import type { Cluster } from "@/lib/clusters";
import { USE_CASE_LABELS, UC_NUMBERS } from "@/lib/types";
import type { UseCaseKey } from "@/lib/types";
import { UC_INSIGHTS } from "@/lib/uc-insights";

interface Props {
  clusters: Cluster[];
  activeIndex: number;
  onSelect: (index: number) => void;
  compact?: boolean;
}

const DRAG_THRESHOLD = 30;
const SLIDE_STEP = 32.83; // % per card+gap
const TRANSITION = "transform 500ms ease-out";

export default function ClusterCarousel({
  clusters,
  activeIndex,
  onSelect,
  compact = false,
}: Props) {
  const count = clusters.length;
  const [flippedIndex, setFlippedIndex] = useState<number | null>(null);

  /* Unflip when navigating away */
  useEffect(() => {
    setFlippedIndex(null);
  }, [activeIndex]);

  /*
   * Slides: [clone-last, 0, 1, ..., N-1, clone-first]
   * internalPos 0 = clone-last, 1..N = real, N+1 = clone-first
   */
  const [internalPos, setInternalPos] = useState(activeIndex + 1);
  const trackRef = useRef<HTMLDivElement>(null);
  const isJumping = useRef(false);

  /* Sync when parent changes activeIndex (e.g. dot click) */
  useEffect(() => {
    if (!isJumping.current) {
      setInternalPos(activeIndex + 1);
    }
    isJumping.current = false;
  }, [activeIndex]);

  /*
   * After the slide animation ends on a clone, do an instant
   * DOM-level jump to the real slide. The reflow trick ensures
   * transition:none + new transform apply in the SAME paint frame,
   * so there's zero visible flicker.
   */
  const handleTransitionEnd = useCallback(() => {
    const track = trackRef.current;
    if (!track) return;

    let jumpTo: number | null = null;
    let realIndex: number | null = null;

    if (internalPos === 0) {
      jumpTo = count; // clone-last → real last
      realIndex = count - 1;
    } else if (internalPos === count + 1) {
      jumpTo = 1; // clone-first → real first
      realIndex = 0;
    }

    if (jumpTo !== null && realIndex !== null) {
      isJumping.current = true;
      // 1. Kill transition
      track.style.transition = "none";
      // 2. Jump to real position
      const newShift = (jumpTo - 1) * SLIDE_STEP;
      track.style.transform = `translateX(-${newShift}%)`;
      // 3. Force reflow so browser applies both changes in one paint
      void track.offsetHeight;
      // 4. Re-enable transition
      track.style.transition = TRANSITION;
      // 5. Update React state + parent
      setInternalPos(jumpTo);
      onSelect(realIndex);
    }
  }, [internalPos, count, onSelect]);

  const goPrev = useCallback(() => {
    setInternalPos((p) => {
      const newPos = p - 1;
      if (newPos >= 1 && newPos <= count) onSelect(newPos - 1);
      return newPos;
    });
  }, [count, onSelect]);

  const goNext = useCallback(() => {
    setInternalPos((p) => {
      const newPos = p + 1;
      if (newPos >= 1 && newPos <= count) onSelect(newPos - 1);
      return newPos;
    });
  }, [count, onSelect]);

  /* Drag / swipe */
  const pointerStart = useRef<number | null>(null);
  const dragging = useRef(false);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    pointerStart.current = e.clientX;
    dragging.current = false;
  }, []);

  const handlePointerUp = useCallback(
    (e: React.PointerEvent) => {
      if (pointerStart.current === null) return;
      const dx = e.clientX - pointerStart.current;
      pointerStart.current = null;
      if (Math.abs(dx) > DRAG_THRESHOLD) {
        dragging.current = true;
        dx < 0 ? goNext() : goPrev();
      }
    },
    [goNext, goPrev],
  );

  if (count === 0) return null;

  /* Slides array */
  const slides = [clusters[count - 1], ...clusters, clusters[0]];
  const shiftPercent = (internalPos - 1) * SLIDE_STEP;
  /*
   * Landing: cards use viewport height so they fill the screen.
   * 50vh = half the viewport height → large, impactful cards.
   * Compact (dashboard): smaller fixed aspect ratio.
   */
  /*
   * Landing: large cards that scale with viewport in both dimensions.
   * Height: 60vh (clamped 250-650px). Width: 31.33% of track (same as compact).
   * The track container itself is full-width, so 31.33% scales with monitor.
   * Compact: smaller aspect-ratio-based cards for dashboard mode.
   */
  const heightStyle = compact ? undefined : "clamp(280px, 70vh, 750px)";
  const aspectRatio = compact ? "16/7" : undefined;

  return (
    <div
      role="region"
      aria-roledescription="carousel"
      aria-label="Themen-Cluster"
      className="flex flex-col items-center select-none w-full"
    >
      <div className="flex items-center w-full max-w-[1600px] px-2">
        {/* Left arrow */}
        <button
          onClick={goPrev}
          aria-label="Vorheriger Cluster"
          className="shrink-0 flex items-center justify-center h-12 w-12 rounded-full border-2 border-[var(--color-accent-gold)] text-[var(--color-accent-gold)] transition-colors hover:bg-[var(--color-accent-gold)]/10 z-10"
        >
          <ChevronLeft className="h-6 w-6" />
        </button>

        {/* Viewport */}
        <div
          className="flex-1 overflow-hidden mx-2"
          onPointerDown={handlePointerDown}
          onPointerUp={handlePointerUp}
        >
          <div
            ref={trackRef}
            className="flex"
            style={{
              gap: "1.5%",
              transform: `translateX(-${shiftPercent}%)`,
              transition: TRANSITION,
            }}
            onTransitionEnd={handleTransitionEnd}
          >
            {slides.map((cluster, i) => {
              const realIdx =
                i === 0 ? count - 1 : i === slides.length - 1 ? 0 : i - 1;
              const isCenter = i === internalPos;
              const dist = Math.abs(i - internalPos);
              const isNeighbor = dist === 1;
              const isFlipped = !compact && isCenter && flippedIndex === realIdx;
              const canFlip = !compact && isCenter && cluster.ucKeys.length > 0;

              return (
                <div
                  key={`${cluster.id}-${i}`}
                  role="group"
                  aria-roledescription="slide"
                  aria-label={`${realIdx + 1} von ${count}: ${cluster.title}`}
                  className="shrink-0 cursor-pointer"
                  style={{
                    width: "31.33%",
                    height: heightStyle,
                    aspectRatio,
                    opacity: isCenter ? 1 : isNeighbor ? 0.65 : 0.35,
                    transform: isCenter ? "scale(1.03)" : "scale(0.97)",
                    filter: isCenter
                      ? "none"
                      : isNeighbor
                        ? "blur(1px)"
                        : "blur(2px)",
                    transition:
                      "transform 0.5s ease, opacity 0.5s ease, filter 0.5s ease",
                  }}
                  onClick={() => {
                    if (dragging.current) {
                      dragging.current = false;
                      return;
                    }
                    if (canFlip) {
                      setFlippedIndex(isFlipped ? null : realIdx);
                    } else {
                      onSelect(realIdx);
                    }
                  }}
                  tabIndex={isCenter ? 0 : -1}
                  onKeyDown={(e) => {
                    if (e.key === "ArrowRight") goNext();
                    if (e.key === "ArrowLeft") goPrev();
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      if (canFlip) {
                        setFlippedIndex(isFlipped ? null : realIdx);
                      } else {
                        onSelect(realIdx);
                      }
                    }
                  }}
                >
                  <div className="relative h-full w-full">
                    {/* ── Front Face ── */}
                    <div
                      className={`absolute inset-0 overflow-hidden rounded-2xl transition-all duration-500 ${
                        isCenter
                          ? "ring-1 ring-[var(--color-accent-gold)]/30 glow-border"
                          : "border border-[var(--color-border)]"
                      }`}
                      style={{
                        opacity: isFlipped ? 0 : 1,
                        transform: isFlipped ? "scaleX(0)" : "scaleX(1)",
                        pointerEvents: isFlipped ? "none" : "auto",
                      }}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={cluster.image}
                        alt=""
                        aria-hidden="true"
                        className="absolute inset-0 h-full w-full object-cover"
                        draggable={false}
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-[#091428] via-[#091428]/60 to-transparent" />
                      <div className="relative z-[2] flex h-full flex-col justify-end p-4">
                        <h3 className="text-sm sm:text-base lg:text-lg font-bold text-white leading-tight">
                          {cluster.title}
                        </h3>
                        {!compact && cluster.description && (
                          <p className="mt-1 text-[10px] sm:text-xs text-white/70 leading-snug line-clamp-2">
                            {cluster.description}
                          </p>
                        )}
                        {canFlip && (
                          <p className="mt-2 text-[10px] text-[var(--color-accent-gold)]/80 font-medium">
                            Klicken für Details
                          </p>
                        )}
                      </div>
                    </div>

                    {/* ── Back Face ── */}
                    <div
                      className="absolute inset-0 overflow-hidden rounded-2xl border border-[var(--color-accent-gold)]/30 bg-[#091428] transition-all duration-500"
                      style={{
                        opacity: isFlipped ? 1 : 0,
                        transform: isFlipped ? "scaleX(1)" : "scaleX(0)",
                        pointerEvents: isFlipped ? "auto" : "none",
                      }}
                    >
                      <div className="flex h-full flex-col p-5 overflow-y-auto">
                        <div className="flex items-center justify-between mb-3">
                          <h3 className="text-sm sm:text-base font-bold text-white">
                            {cluster.title}
                          </h3>
                          <RotateCcw className="h-4 w-4 text-[var(--color-accent-gold)]/60" />
                        </div>
                        <p className="text-[10px] sm:text-xs text-white/50 mb-4">
                          Dieser Analysebereich umfasst:
                        </p>
                        <div className="flex flex-col gap-3 flex-1">
                          {cluster.ucKeys.map((ucKey: UseCaseKey) => (
                            <div key={ucKey} className="flex gap-2">
                              <span className="shrink-0 mt-0.5 rounded bg-[var(--color-accent-gold)]/20 px-1.5 py-0.5 text-[10px] font-bold text-[var(--color-accent-gold)]">
                                UC{UC_NUMBERS[ucKey].number}
                              </span>
                              <div className="min-w-0">
                                <p className="text-xs font-semibold text-white/90 leading-tight">
                                  {USE_CASE_LABELS[ucKey]}
                                </p>
                                <p className="mt-0.5 text-[10px] leading-snug text-white/50 line-clamp-2">
                                  {UC_INSIGHTS[ucKey]}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                        <p className="mt-3 text-[10px] text-[var(--color-accent-gold)]/60 font-medium text-center">
                          Klicken zum Zurück
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right arrow */}
        <button
          onClick={goNext}
          aria-label="Nächster Cluster"
          className="shrink-0 flex items-center justify-center h-12 w-12 rounded-full border-2 border-[var(--color-accent-gold)] text-[var(--color-accent-gold)] transition-colors hover:bg-[var(--color-accent-gold)]/10 z-10"
        >
          <ChevronRight className="h-6 w-6" />
        </button>
      </div>

      {/* Navigation dots */}
      <nav
        aria-label="Cluster-Navigation"
        className="mt-5 flex items-center justify-center gap-2"
      >
        {clusters.map((cluster, i) => (
          <button
            key={cluster.id}
            aria-label={`Zu ${cluster.title} wechseln`}
            aria-current={i === activeIndex ? "true" : undefined}
            className={`h-2 rounded-full transition-all duration-300 ${
              i === activeIndex
                ? "w-6 bg-[var(--color-accent-gold)]"
                : "w-2 bg-[var(--color-text-muted)]/40 hover:bg-[var(--color-text-muted)]/70"
            }`}
            onClick={() => onSelect(i)}
          />
        ))}
      </nav>
    </div>
  );
}
