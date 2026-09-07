/**
 * drawOcean — Sky gradient, star field, wave layers, safe-destination landmark.
 */
import {
  scrollMap, scrollMapColor, lerp,
  getHorizonRatio, SHIP_WAVE_LAYER, TOTAL_WAVE_LAYERS,
} from './types.js';

/* ── Colour breakpoints (compressed 0–75%) ── */

const SKY_TOP = [
  [0, '#1a3a5c'], [0.15, '#152e4a'], [0.30, '#0c1620'],
  [0.42, '#080c14'], [0.52, '#0e1e30'], [0.64, '#1e5080'], [0.75, '#2a6898'],
];
const SKY_BOT = [
  [0, '#0e2440'], [0.15, '#0c1c32'], [0.30, '#060c14'],
  [0.42, '#050a10'], [0.52, '#0a1828'], [0.64, '#0c3050'], [0.75, '#14466a'],
];
const OCEAN_TOP = [
  [0, '#0a1e38'], [0.30, '#080e18'], [0.42, '#060a12'],
  [0.56, '#0a1828'], [0.75, '#0e2a48'],
];

/* ── Wave amplitude envelope ── */

const AMP = [
  [0, 16], [0.15, 24], [0.26, 50], [0.34, 85],
  [0.42, 110], [0.50, 75], [0.58, 38], [0.68, 18], [0.75, 10],
];

/* ── Storm intensity ── */

const STORM = [
  [0, 0], [0.15, 0], [0.30, 0.5], [0.38, 1],
  [0.50, 0.7], [0.58, 0.2], [0.68, 0], [1, 0],
];

/* ─────────────────── public wave helpers ─────────────────── */

/** Wave-surface Y at position `x` for a given layer index. */
export function waveY(x, t, s, layer, _w, h) {
  const amp = scrollMap(s, AMP) * (0.4 + layer * 0.16);
  const wl  = 0.0038 - layer * 0.0005;
  const spd = (layer % 2 === 0 ? 1 : -0.7) * (0.5 + layer * 0.12);
  const horizonRatio = getHorizonRatio(s);
  const baseY = h * (horizonRatio + 0.06 + layer * 0.085);

  return (
    baseY +
    Math.sin(x * wl + t * spd + layer * 1.3) * amp +
    Math.cos(x * wl * 1.6 - t * spd * 0.5) * amp * 0.3 +
    Math.sin(x * 0.005 + t * 0.9 + layer * 0.7) * amp * 0.1
  );
}

/** Wave slope (atan2) at `x` for ship tilt. */
export function waveSlope(x, t, s, layer, w, h) {
  const d = 3;
  return Math.atan2(
    waveY(x + d, t, s, layer, w, h) - waveY(x - d, t, s, layer, w, h),
    d * 2,
  );
}

/* ─────────────────── draw entry point ─────────────────── */

export function drawOcean(rc) {
  const { ctx, width: w, height: h, time: t, scroll: s, isMobile } = rc;
  const step = isMobile ? 10 : 6;
  const horizonRatio = getHorizonRatio(s);

  /* ── sky ── */
  const skyG = ctx.createLinearGradient(0, 0, 0, h * horizonRatio);
  skyG.addColorStop(0, scrollMapColor(s, SKY_TOP));
  skyG.addColorStop(1, scrollMapColor(s, SKY_BOT));
  ctx.fillStyle = skyG;
  ctx.fillRect(0, 0, w, h * horizonRatio + 2);

  /* ── stars (visible in calm phases) ── */
  const starA = scrollMap(s, [[0, 0.3], [0.15, 0.2], [0.26, 0], [0.58, 0], [0.68, 0.15], [0.75, 0.35], [0.82, 0.0]]);
  if (starA > 0.01) {
    for (let i = 0; i < 25; i++) {
      const sx = (i * 137.5 + 42) % w;
      const sy = (i * 83.7 + 17) % (h * horizonRatio * 0.8);
      const r  = ((i * 7 + 3) % 3) * 0.4 + 0.4;
      const tw = Math.sin(t * (0.5 + i * 0.1) + i) * 0.3 + 0.7;
      ctx.beginPath();
      ctx.arc(sx, sy, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200,210,230,${starA * tw})`;
      ctx.fill();
    }
  }

  /* ── ocean base ── */
  const oG = ctx.createLinearGradient(0, h * horizonRatio, 0, h);
  oG.addColorStop(0, scrollMapColor(s, OCEAN_TOP));
  oG.addColorStop(1, '#020810');
  ctx.fillStyle = oG;
  ctx.fillRect(0, h * horizonRatio, w, h);

  /* ── safe-destination landmark (island + lighthouse) ── */
  const destA = scrollMap(s, [[0, 0], [0.60, 0], [0.68, 0.35], [0.75, 0.85], [0.80, 0.0]]);
  if (destA > 0.01) {
    const hLine = h * horizonRatio;
    ctx.fillStyle = `rgba(15,30,50,${destA})`;
    ctx.beginPath();
    ctx.moveTo(w * 0.80, hLine);
    ctx.quadraticCurveTo(w * 0.84, hLine - 22 * destA, w * 0.88, hLine);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = `rgba(160,170,180,${destA})`;
    ctx.fillRect(w * 0.839, hLine - 26 * destA, 2.5, 14 * destA);

    if (Math.sin(t * 2) > 0) {
      ctx.beginPath();
      ctx.arc(w * 0.84, hLine - 28 * destA, 3, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,220,100,${destA * 0.8})`;
      ctx.fill();
    }
  }

  /* ── background wave layers (0 → SHIP_WAVE_LAYER) ── */
  for (let i = 0; i <= SHIP_WAVE_LAYER; i++) drawWaveLayer(ctx, w, h, t, s, i, step);

  /* ── return deferred foreground drawer ── */
  return () => {
    for (let i = SHIP_WAVE_LAYER + 1; i < TOTAL_WAVE_LAYERS; i++) drawWaveLayer(ctx, w, h, t, s, i, step);
  };
}

/* ─────────────────── single wave layer ─────────────────── */

function drawWaveLayer(ctx, w, h, t, s, layer, step) {
  const storm = scrollMap(s, STORM);
  const depth = layer / TOTAL_WAVE_LAYERS;
  const r = Math.max(0, Math.round(lerp(4, 14, depth) - storm * 5));
  const g = Math.max(0, Math.round(lerp(24, 58, depth) - storm * 18));
  const b = Math.max(0, Math.round(lerp(48, 98, depth) - storm * 22));
  const a = lerp(0.45, 0.88, depth);

  ctx.beginPath();
  ctx.moveTo(0, h);
  for (let x = 0; x <= w; x += step) ctx.lineTo(x, waveY(x, t, s, layer, w, h));
  ctx.lineTo(w, h);
  ctx.closePath();
  ctx.fillStyle = `rgba(${r},${g},${b},${a})`;
  ctx.fill();

  if (storm > 0.15 || layer >= TOTAL_WAVE_LAYERS - 2) {
    const fa = lerp(0.02, 0.12, storm) * (layer >= TOTAL_WAVE_LAYERS - 2 ? 1.3 : 0.8);
    ctx.strokeStyle = `rgba(180,210,235,${fa})`;
    ctx.lineWidth = lerp(0.5, 1.4, storm);
    ctx.stroke();
  }
}
