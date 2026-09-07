/**
 * drawAtmosphere — Renders the Top 50% White Cloud Sky, volumetric realistic clouds,
 * soft atmospheric horizon haze, storm sky darkening, lightning engine,
 * golden dawn recovery, and safe haven lighthouse.
 */
import { RenderContext, scrollMap, scrollMapColor, HORIZON_RATIO, lerp } from './types';

// Dynamic Sky Top color palette across scroll journey:
// 0.00: Bright luminous sky with pale blue tone
// 0.22: Darkening overcast silver-gray
// 0.38: Storm twilight charcoal
// 0.52: Peak storm violent dark midnight indigo
// 0.68: Satellite upper atmosphere clear glow
// 0.82: Warm golden dawn break
// 1.00: Serene bright azure morning sky
const SKY_TOP_COLORS: [number, string][] = [
  [0.00, '#e0f2fe'], // Bright pale sky-blue / white
  [0.18, '#94a3b8'], // Soft overcast slate
  [0.32, '#334155'], // Dark storm blue-grey
  [0.48, '#090d16'], // Deep storm charcoal
  [0.60, '#0f172a'], // High-altitude stratosphere
  [0.72, '#1e293b'], // Pre-dawn clear
  [0.85, '#fdba74'], // Golden sunrise break
  [1.00, '#bae6fd'], // Serene morning sky
];

const SKY_HORIZON_COLORS: [number, string][] = [
  [0.00, '#ffffff'], // Luminous pure white soft horizon
  [0.18, '#cbd5e1'], // Soft grey horizon haze
  [0.32, '#475569'], // Stormy horizon
  [0.48, '#0b1120'], // Thunderous sea horizon
  [0.60, '#1e293b'],
  [0.72, '#334155'],
  [0.85, '#fed7aa'], // Warm golden horizon
  [1.00, '#f0f9ff'], // Clean bright horizon
];

// Pre-generated volumetric cloud clusters for 3 depth layers
interface CloudPuff {
  relX: number;     // 0.0 -> 1.0
  relY: number;     // 0.0 -> 1.0 of sky portion
  radius: number;   // px
  speed: number;    // drift speed
  density: number;  // opacity factor
  layer: number;    // 0 = high/cirrus, 1 = mid/cumulus, 2 = low/foreground
}

const CLOUDS: CloudPuff[] = [];
// High cirrus sheets
for (let i = 0; i < 8; i++) {
  CLOUDS.push({
    relX: (i * 0.14 + 0.05) % 1.0,
    relY: 0.08 + (i * 0.05) % 0.22,
    radius: 90 + (i % 4) * 35,
    speed: 0.008 + (i % 3) * 0.004,
    density: 0.25 + (i % 3) * 0.10,
    layer: 0,
  });
}
// Mid cumulus puffs (fluffy, realistic cloud bodies)
for (let i = 0; i < 18; i++) {
  CLOUDS.push({
    relX: (i * 0.08 + 0.02) % 1.0,
    relY: 0.14 + (i * 0.06) % 0.26,
    radius: 55 + (i % 5) * 22,
    speed: 0.016 + (i % 4) * 0.006,
    density: 0.45 + (i % 3) * 0.15,
    layer: 1,
  });
}
// Foreground wisps
for (let i = 0; i < 10; i++) {
  CLOUDS.push({
    relX: (i * 0.11 + 0.07) % 1.0,
    relY: 0.22 + (i * 0.04) % 0.20,
    radius: 40 + (i % 3) * 20,
    speed: 0.028 + (i % 2) * 0.01,
    density: 0.35 + (i % 2) * 0.12,
    layer: 2,
  });
}

// Lightning state
let lightningIntensity = 0;
let nextLightningTime = 2.5;
let lightningBranch: { x: number; y: number }[] = [];

export function drawAtmosphere(rc: RenderContext): void {
  const { ctx, width, height, time, scroll, mouseX, mouseY, isMobile } = rc;
  const horizonY = height * HORIZON_RATIO + mouseY * 12;

  /* ── 1. Top 50% Sky Gradient (Bright White/Blue Sky -> Storm -> Dawn) ── */
  const topColor = scrollMapColor(scroll, SKY_TOP_COLORS);
  const horizonColor = scrollMapColor(scroll, SKY_HORIZON_COLORS);

  const skyGrad = ctx.createLinearGradient(0, 0, 0, horizonY + 30);
  skyGrad.addColorStop(0, topColor);
  skyGrad.addColorStop(0.85, horizonColor);
  skyGrad.addColorStop(1, horizonColor);

  ctx.fillStyle = skyGrad;
  ctx.fillRect(0, 0, width, horizonY + 35);

  /* ── 2. Soft Realistic White Clouds with Parallax & Storm Darkening ── */
  // Cloud shading shifts from brilliant white to deep stormy slate
  const stormDarkness = scrollMap(scroll, [
    [0.00, 0.0],
    [0.20, 0.25],
    [0.35, 0.70],
    [0.52, 0.95],
    [0.65, 0.60],
    [0.78, 0.20],
    [0.90, 0.05],
    [1.00, 0.0],
  ]);

  // Cloud RGB color interpolation
  const cloudR = Math.round(lerp(255, 25, stormDarkness));
  const cloudG = Math.round(lerp(255, 35, stormDarkness));
  const cloudB = Math.round(lerp(255, 55, stormDarkness));
  const cloudShadeR = Math.round(lerp(220, 15, stormDarkness));
  const cloudShadeG = Math.round(lerp(235, 20, stormDarkness));
  const cloudShadeB = Math.round(lerp(248, 35, stormDarkness));

  ctx.save();
  for (let i = 0; i < CLOUDS.length; i++) {
    const c = CLOUDS[i];
    // Parallax speed based on layer & mouse
    const layerSpeed = (c.layer + 1) * 0.5;
    const driftX = ((c.relX * width + time * c.speed * 40 + mouseX * 25 * layerSpeed) % (width + c.radius * 2)) - c.radius;
    const puffY = c.relY * horizonY + mouseY * 10 * layerSpeed;
    const r = c.radius * (isMobile ? 0.7 : 1.0);

    // Volumetric soft radial gradient puff
    const puffGrad = ctx.createRadialGradient(driftX, puffY - r * 0.2, r * 0.1, driftX, puffY, r);
    puffGrad.addColorStop(0, `rgba(${cloudR}, ${cloudG}, ${cloudB}, ${c.density * (0.8 + stormDarkness * 0.3)})`);
    puffGrad.addColorStop(0.55, `rgba(${cloudShadeR}, ${cloudShadeG}, ${cloudShadeB}, ${c.density * 0.65})`);
    puffGrad.addColorStop(1, `rgba(${cloudShadeR}, ${cloudShadeG}, ${cloudShadeB}, 0)`);

    ctx.fillStyle = puffGrad;
    ctx.beginPath();
    ctx.arc(driftX, puffY, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();

  /* ── 3. Golden Dawn / Sunrise Break (Recovery Phase: 0.76 - 0.94) ── */
  const dawnGlow = scrollMap(scroll, [
    [0.00, 0],
    [0.72, 0],
    [0.82, 0.90],
    [0.92, 0.40],
    [1.00, 0.10],
  ]);

  if (dawnGlow > 0.02) {
    ctx.save();
    const sunX = width * 0.76 + mouseX * 20;
    const sunY = horizonY - 15;

    // Radiant Sun Flare
    const dawnGrad = ctx.createRadialGradient(sunX, sunY, 5, sunX, sunY, width * 0.4);
    dawnGrad.addColorStop(0, `rgba(255, 240, 180, ${0.75 * dawnGlow})`);
    dawnGrad.addColorStop(0.3, `rgba(251, 146, 60, ${0.45 * dawnGlow})`);
    dawnGrad.addColorStop(0.7, `rgba(217, 70, 239, ${0.15 * dawnGlow})`);
    dawnGrad.addColorStop(1, 'transparent');

    ctx.fillStyle = dawnGrad;
    ctx.fillRect(0, 0, width, horizonY + 20);

    // Glowing Sun Orb
    ctx.beginPath();
    ctx.arc(sunX, sunY, 34, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255, 250, 220, ${0.95 * dawnGlow})`;
    ctx.shadowColor = '#fbbf24';
    ctx.shadowBlur = 24;
    ctx.fill();
    ctx.restore();
  }

  /* ── 4. Lightning Engine (Peak Storm 0.40 - 0.62) ── */
  const stormIntensity = scrollMap(scroll, [
    [0.00, 0],
    [0.36, 0],
    [0.46, 0.85],
    [0.55, 1.0],
    [0.62, 0.35],
    [0.70, 0],
  ]);

  if (stormIntensity > 0.1) {
    if (time > nextLightningTime) {
      lightningIntensity = 1.0;
      nextLightningTime = time + 2.2 + Math.random() * 3.2;

      lightningBranch = [];
      let lx = width * (0.25 + Math.random() * 0.5);
      let ly = 10;
      lightningBranch.push({ x: lx, y: ly });
      while (ly < horizonY * 0.9) {
        lx += (Math.random() - 0.5) * 50;
        ly += 16 + Math.random() * 24;
        lightningBranch.push({ x: lx, y: ly });
      }
    }

    if (lightningIntensity > 0.02) {
      lightningIntensity *= 0.88;

      // Full atmospheric flash
      ctx.fillStyle = `rgba(230, 240, 255, ${0.45 * lightningIntensity * stormIntensity})`;
      ctx.fillRect(0, 0, width, height);

      // Jagged electrical discharge bolt
      if (lightningBranch.length > 2) {
        ctx.save();
        ctx.strokeStyle = `rgba(255, 255, 255, ${0.95 * lightningIntensity})`;
        ctx.lineWidth = 3.0;
        ctx.shadowColor = '#00f2fe';
        ctx.shadowBlur = 22;
        ctx.beginPath();
        ctx.moveTo(lightningBranch[0].x, lightningBranch[0].y);
        for (let b = 1; b < lightningBranch.length; b++) {
          ctx.lineTo(lightningBranch[b].x, lightningBranch[b].y);
        }
        ctx.stroke();
        ctx.restore();
      }
    }
  }

  /* ── 5. Distant Safe Harbor & Lighthouse (Recovery & Calm End: 0.78 - 1.00) ── */
  const havenVisibility = scrollMap(scroll, [
    [0.00, 0],
    [0.76, 0],
    [0.85, 0.8],
    [1.00, 1.0],
  ]);

  if (havenVisibility > 0.02) {
    ctx.save();
    const lhBaseX = width * 0.82 + mouseX * 12;
    const lhBaseY = horizonY;

    // Distant Island Silhouette
    ctx.fillStyle = `rgba(15, 35, 60, ${0.85 * havenVisibility})`;
    ctx.beginPath();
    ctx.moveTo(lhBaseX - 80, lhBaseY);
    ctx.quadraticCurveTo(lhBaseX - 25, lhBaseY - 16, lhBaseX, lhBaseY - 14);
    ctx.quadraticCurveTo(lhBaseX + 40, lhBaseY - 18, lhBaseX + 90, lhBaseY);
    ctx.closePath();
    ctx.fill();

    // Lighthouse Tower
    ctx.fillStyle = `rgba(30, 50, 80, ${havenVisibility})`;
    ctx.beginPath();
    ctx.moveTo(lhBaseX - 4, lhBaseY - 10);
    ctx.lineTo(lhBaseX + 4, lhBaseY - 10);
    ctx.lineTo(lhBaseX + 2.5, lhBaseY - 36);
    ctx.lineTo(lhBaseX - 2.5, lhBaseY - 36);
    ctx.closePath();
    ctx.fill();

    // Lantern Room
    ctx.fillStyle = `rgba(255, 235, 150, ${havenVisibility})`;
    ctx.fillRect(lhBaseX - 3.5, lhBaseY - 40, 7, 4.5);

    // Rotating Lighthouse Light Beam
    const beamAngle = time * 1.6;
    const beamX = lhBaseX;
    const beamY = lhBaseY - 38;
    const beamLen = width * 0.38;
    const beamSpread = 0.22;

    const b1x = beamX + Math.cos(beamAngle - beamSpread) * beamLen;
    const b1y = beamY + Math.sin(beamAngle - beamSpread) * (beamLen * 0.3);
    const b2x = beamX + Math.cos(beamAngle + beamSpread) * beamLen;
    const b2y = beamY + Math.sin(beamAngle + beamSpread) * (beamLen * 0.3);

    const beamGrad = ctx.createRadialGradient(beamX, beamY, 2, beamX, beamY, beamLen);
    beamGrad.addColorStop(0, `rgba(255, 248, 190, ${0.8 * havenVisibility})`);
    beamGrad.addColorStop(0.35, `rgba(255, 220, 130, ${0.35 * havenVisibility})`);
    beamGrad.addColorStop(1, 'transparent');

    ctx.fillStyle = beamGrad;
    ctx.beginPath();
    ctx.moveTo(beamX, beamY);
    ctx.lineTo(b1x, b1y);
    ctx.lineTo(b2x, b2y);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
  }

  /* ── 6. Middle: Soft Atmospheric Horizon Haze (Seamless Sky-to-Ocean Blend) ── */
  ctx.save();
  const hazeHeight = 70;
  const hazeGrad = ctx.createLinearGradient(0, horizonY - hazeHeight * 0.4, 0, horizonY + hazeHeight * 0.6);
  hazeGrad.addColorStop(0, 'transparent');
  hazeGrad.addColorStop(0.45, `rgba(224, 242, 254, ${0.75 * (1 - stormDarkness * 0.6)})`);
  hazeGrad.addColorStop(0.7, `rgba(14, 116, 144, ${0.45 * (1 - stormDarkness * 0.5)})`);
  hazeGrad.addColorStop(1, 'transparent');

  ctx.fillStyle = hazeGrad;
  ctx.fillRect(0, horizonY - hazeHeight * 0.4, width, hazeHeight);
  ctx.restore();
}
