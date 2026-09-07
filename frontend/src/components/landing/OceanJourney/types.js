/**
 * Shared types, math utilities, and scene constants
 * for the Cinematic Ocean Journey animation.
 */

/* ── Math Utilities ── */

export const lerp = (a, b, t) => a + (b - a) * t;

export const clamp = (val, min, max) =>
  Math.max(min, Math.min(max, val));

export const smoothstep = (min, max, value) => {
  const x = clamp((value - min) / (max - min), 0, 1);
  return x * x * (3 - 2 * x);
};

/**
 * Multi-stop piecewise linear interpolation for numbers based on scroll position.
 */
export function scrollMap(scroll, stops) {
  if (stops.length === 0) return 0;
  if (scroll <= stops[0][0]) return stops[0][1];
  for (let i = 1; i < stops.length; i++) {
    if (scroll <= stops[i][0]) {
      const prev = stops[i - 1];
      const curr = stops[i];
      const span = curr[0] - prev[0];
      if (span === 0) return curr[1];
      const t = (scroll - prev[0]) / span;
      return lerp(prev[1], curr[1], t);
    }
  }
  return stops[stops.length - 1][1];
}

/**
 * Interpolates between two hex colors (#RRGGBB).
 */
export function lerpColor(hexA, hexB, t) {
  const parseHex = (hex) => {
    const clean = hex.replace('#', '');
    return [
      parseInt(clean.substring(0, 2), 16) || 0,
      parseInt(clean.substring(2, 4), 16) || 0,
      parseInt(clean.substring(4, 6), 16) || 0,
    ];
  };

  const a = parseHex(hexA);
  const b = parseHex(hexB);

  const r = Math.round(lerp(a[0], b[0], t));
  const g = Math.round(lerp(a[1], b[1], t));
  const bl = Math.round(lerp(a[2], b[2], t));

  return `rgb(${r}, ${g}, ${bl})`;
}

/**
 * Multi-stop piecewise color interpolation based on scroll position.
 */
export function scrollMapColor(scroll, stops) {
  if (stops.length === 0) return '#000000';
  if (scroll <= stops[0][0]) return stops[0][1];
  for (let i = 1; i < stops.length; i++) {
    if (scroll <= stops[i][0]) {
      const prev = stops[i - 1];
      const curr = stops[i];
      const span = curr[0] - prev[0];
      if (span === 0) return curr[1];
      const t = (scroll - prev[0]) / span;
      return lerpColor(prev[1], curr[1], t);
    }
  }
  return stops[stops.length - 1][1];
}

/* ── Scene Positioning Constants & Dynamic Helpers ── */

/** Horizon base Y position at ~48% from top for 0–75% scroll */
export const HORIZON_RATIO = 0.48;

/** Horizon ratio: stays at 0.48 from 0–75% scroll, then raises smoothly upward to submerge */
export function getHorizonRatio(scroll) {
  return scrollMap(scroll, [
    [0.00, 0.48],
    [0.75, 0.48],
    [0.82, 0.20],
    [0.88, -0.04],
    [0.94, -0.15],
    [1.00, -0.20],
  ]);
}

/** Ship horizontal position at 50% */
export const SHIP_X_RATIO = 0.50;

/** Total wave layers (Background 0, 1 -> Ship -> Foreground 2, 3, 4) */
export const TOTAL_WAVE_LAYERS = 5;

/** The wave layer index that the ship physically rests upon */
export const SHIP_WAVE_LAYER = 2;
