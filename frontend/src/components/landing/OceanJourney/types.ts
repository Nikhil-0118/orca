/**
 * Shared types, interfaces, math utilities, and scene constants
 * for the Cinematic Ocean Journey animation (Two-Sided Layout: Left Text / Center Ship / Right Telemetry).
 */

export interface RenderContext {
  ctx: CanvasRenderingContext2D;
  width: number;
  height: number;
  time: number;          // continuous time in seconds
  scroll: number;        // smoothed scroll progress 0.0 -> 1.0
  isMobile: boolean;
  mouseX: number;        // normalized mouse -0.5 -> 0.5
  mouseY: number;        // normalized mouse -0.5 -> 0.5
}

/* ── Math Utilities ── */

export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export const clamp = (val: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, val));

export const smoothstep = (min: number, max: number, value: number): number => {
  const x = clamp((value - min) / (max - min), 0, 1);
  return x * x * (3 - 2 * x);
};

/**
 * Multi-stop piecewise linear interpolation for numbers based on scroll position.
 */
export function scrollMap(scroll: number, stops: [number, number][]): number {
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
export function lerpColor(hexA: string, hexB: string, t: number): string {
  const parseHex = (hex: string) => {
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
export function scrollMapColor(scroll: number, stops: [number, string][]): string {
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

/* ── Scene Positioning Constants ── */

/** Horizon base Y position at ~48% from top (divides 50% sky / 50% ocean) */
export const HORIZON_RATIO = 0.48;

/** Ship horizontal position at 50% (exact center of the open 45% safe zone!) */
export const SHIP_X_RATIO = 0.50;

/** Total wave layers (Background 0, 1 -> Ship -> Foreground 2, 3, 4) */
export const TOTAL_WAVE_LAYERS = 5;

/** The wave layer index that the ship physically rests upon */
export const SHIP_WAVE_LAYER = 2;
