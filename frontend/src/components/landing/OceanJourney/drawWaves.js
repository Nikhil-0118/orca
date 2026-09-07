/**
 * drawWaves — Procedural ocean wave simulation compressed into 0–75% scroll.
 */
import {
  scrollMap,
  lerp,
  getHorizonRatio,
  TOTAL_WAVE_LAYERS,
  SHIP_WAVE_LAYER,
} from './types.js';

// Wave amplitude envelope across scroll journey (Calm -> Rough -> Storm -> Recovery -> Calm inside 0–75%)
const WAVE_AMPLITUDES = [
  [0.00, 18],  // Gentle calm swells
  [0.12, 32],  // Swells building
  [0.22, 64],  // Rough chop
  [0.34, 110], // Heavy storm surge
  [0.42, 138], // Peak storm towering waves
  [0.50, 92],  // Satellite rescue
  [0.58, 42],  // Subsiding recovery
  [0.68, 20],  // Harbor water
  [0.75, 14],  // Serene calm
  [0.82, 8],   // Transition
  [1.00, 4],
];

// Wave speed multiplier
const WAVE_SPEEDS = [
  [0.00, 0.8],
  [0.15, 1.2],
  [0.38, 2.4],
  [0.52, 1.6],
  [0.64, 0.9],
  [0.75, 0.65],
  [1.00, 0.5],
];

// Foam intensity
const FOAM_INTENSITY = [
  [0.00, 0.10],
  [0.14, 0.25],
  [0.28, 0.75],
  [0.42, 1.00],
  [0.52, 0.60],
  [0.62, 0.20],
  [0.72, 0.05],
  [1.00, 0.0],
];

/**
 * Calculates the exact vertical Y coordinate of a wave layer at coordinate X.
 */
export function getWaveY(
  x,
  time,
  scroll,
  layer,
  _width,
  height,
  mouseY = 0,
) {
  const baseAmp = scrollMap(scroll, WAVE_AMPLITUDES);
  const speedMult = scrollMap(scroll, WAVE_SPEEDS);
  const layerFraction = layer / (TOTAL_WAVE_LAYERS - 1);
  const horizonRatio = getHorizonRatio(scroll);

  const baseY = height * (horizonRatio + 0.04 + layerFraction * 0.40) + mouseY * (layer + 1) * 6;

  const layerAmp = baseAmp * (0.38 + layerFraction * 0.78);
  const wavelength = 0.0028 - layerFraction * 0.00055;
  const dir = layer % 2 === 0 ? 1 : -0.8;
  const spd = dir * (0.55 + layerFraction * 0.35) * speedMult;

  const phase1 = x * wavelength + time * spd + layer * 1.7;
  const h1 = Math.sin(phase1) * layerAmp;
  const h2 = Math.sin(phase1 * 2 + 0.4) * (layerAmp * 0.28);
  const h3 = Math.cos(x * (wavelength * 1.6) - time * spd * 0.7 + layer) * (layerAmp * 0.20);
  const h4 = Math.sin(x * 0.006 + time * 1.8 + layer * 2) * (layerAmp * 0.08);

  return baseY + h1 - h2 + h3 + h4;
}

/**
 * Calculates the derivative slope angle (radians) of a wave at coordinate X.
 */
export function getWaveSlope(
  x,
  time,
  scroll,
  layer,
  width,
  height,
  mouseY = 0,
) {
  const delta = 5;
  const y1 = getWaveY(x - delta, time, scroll, layer, width, height, mouseY);
  const y2 = getWaveY(x + delta, time, scroll, layer, width, height, mouseY);
  return Math.atan2(y2 - y1, delta * 2);
}

/**
 * Draws wave layers from `startLayer` to `endLayer` (inclusive).
 */
export function drawWaveLayersRange(
  rc,
  startLayer,
  endLayer,
) {
  const { ctx, width, height, time, scroll, isMobile, mouseY } = rc;
  const step = isMobile ? 12 : 7;
  const foam = scrollMap(scroll, FOAM_INTENSITY);
  const horizonRatio = getHorizonRatio(scroll);

  // Recovery golden sunlight sheen factor (0.56 - 0.72)
  const sunSheen = scrollMap(scroll, [
    [0.00, 0.0],
    [0.54, 0.0],
    [0.62, 0.85],
    [0.70, 0.30],
    [0.76, 0.0],
  ]);

  for (let layer = startLayer; layer <= endLayer; layer++) {
    const depthFrac = layer / (TOTAL_WAVE_LAYERS - 1);

    const stormDarken = foam * 0.48;
    const r = Math.max(0, Math.round(lerp(8, 16, depthFrac) * (1 - stormDarken)));
    const g = Math.max(0, Math.round(lerp(72, 38, depthFrac) * (1 - stormDarken * 0.6)));
    const b = Math.max(0, Math.round(lerp(148, 78, depthFrac) * (1 - stormDarken * 0.4)));
    const alpha = lerp(0.68, 0.96, depthFrac);

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(0, height);

    for (let x = 0; x <= width; x += step) {
      const y = getWaveY(x, time, scroll, layer, width, height, mouseY);
      if (x === 0) {
        ctx.lineTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }

    ctx.lineTo(width, height);
    ctx.closePath();

    const waveGrad = ctx.createLinearGradient(0, height * horizonRatio, 0, height);
    waveGrad.addColorStop(0, `rgba(${r + 10}, ${g + 30}, ${b + 40}, ${alpha * 0.9})`);
    waveGrad.addColorStop(0.4, `rgba(${r}, ${g}, ${b}, ${alpha})`);
    waveGrad.addColorStop(1, `rgba(${Math.max(0, r - 5)}, ${Math.max(0, g - 15)}, ${Math.max(0, b - 20)}, 0.98)`);

    ctx.fillStyle = waveGrad;
    ctx.fill();

    // Specular Sunlight Reflection
    if (sunSheen > 0.05) {
      ctx.save();
      const sheenX = width * 0.76;
      const sheenGrad = ctx.createRadialGradient(sheenX, height * 0.55, 20, sheenX, height * 0.7, width * 0.35);
      sheenGrad.addColorStop(0, `rgba(255, 230, 160, ${0.35 * sunSheen * depthFrac})`);
      sheenGrad.addColorStop(0.5, `rgba(251, 146, 60, ${0.15 * sunSheen * depthFrac})`);
      sheenGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = sheenGrad;
      ctx.fill();
      ctx.restore();
    }

    // Glowing Crest Highlight Stroke
    const crestAlpha = lerp(0.25, 0.75, depthFrac) * (1 + foam * 0.6);
    ctx.strokeStyle = `rgba(0, 242, 254, ${Math.min(0.98, crestAlpha)})`;
    ctx.lineWidth = lerp(1.5, 3.2, depthFrac) * (1 + foam * 0.35);
    ctx.stroke();

    // Surface Ripple Texture
    if (layer >= SHIP_WAVE_LAYER) {
      ctx.strokeStyle = `rgba(255, 255, 255, ${0.12 * (1 - foam * 0.4)})`;
      ctx.lineWidth = 1.0;
      ctx.beginPath();
      for (let rx = (time * 25 + layer * 70) % 80; rx < width; rx += 90) {
        const ry = getWaveY(rx, time, scroll, layer, width, height, mouseY) + 8;
        ctx.moveTo(rx, ry);
        ctx.lineTo(rx + 35, ry - 1);
      }
      ctx.stroke();
    }

    // Dynamic Whitecap Foam
    if (foam > 0.12 && layer >= SHIP_WAVE_LAYER) {
      ctx.save();
      for (let x = 20; x < width; x += (isMobile ? 30 : 18)) {
        const y = getWaveY(x, time, scroll, layer, width, height, mouseY);
        const slope = Math.abs(getWaveSlope(x, time, scroll, layer, width, height, mouseY));

        if (slope > 0.12) {
          const foamSize = (slope * 22 + foam * 12) * (layer >= 3 ? 1.5 : 1.1);
          ctx.fillStyle = `rgba(240, 252, 255, ${0.65 * foam})`;
          ctx.beginPath();
          ctx.ellipse(x, y - 2, foamSize, foamSize * 0.4, 0, 0, Math.PI * 2);
          ctx.fill();

          if (foam > 0.4 && Math.sin(x + time * 5) > 0.3) {
            ctx.fillStyle = `rgba(255, 255, 255, ${0.5 * foam})`;
            ctx.beginPath();
            ctx.arc(x + (Math.sin(x) * 8), y - 6 - (Math.cos(x) * 6), 1.8, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
      ctx.restore();
    }

    ctx.restore();
  }
}
