/**
 * drawShip — Large Marine Research Vessel with complete 0–75% scroll journey:
 * 1. 0–22%: Cruises center position (0.50)
 * 2. 22–45%: Travels to far-left edge (0.09) as storm peaks
 * 3. 45–58%: Holds left position under satellite laser rescue
 * 4. 58–72%: Weather clears, cruises to safe haven harbor & lighthouse
 * 5. 75–82%: Smoothly transitions toward the right edge and exits screen
 */
import {
  scrollMap,
  lerp,
  SHIP_WAVE_LAYER,
} from './types.js';
import { getWaveY, getWaveSlope } from './drawWaves.js';

export function drawShip(rc) {
  const { ctx, width, height, time, scroll, mouseY, isMobile } = rc;

  // Complete story timeline compressed into 0–75%, with exit at 75%+
  const shipXRatio = scrollMap(scroll, [
    [0.00, 0.50],
    [0.22, 0.50],
    [0.45, 0.09],
    [0.58, 0.09],
    [0.64, 0.35],
    [0.72, 0.70],
    [0.75, 0.76],
    [0.80, 1.08],
    [0.85, 1.35],
    [1.00, 1.45],
  ]);

  // Peaceful calm factor (peaks at harbor arrival 0.60–0.75)
  const calmFactor = scrollMap(scroll, [
    [0.00, 0.0],
    [0.58, 0.0],
    [0.68, 0.7],
    [0.75, 1.0],
    [1.00, 1.0],
  ]);

  const surgeAmp = lerp(8, 3.0, calmFactor);
  const forwardSurge = Math.sin(time * (0.4 - calmFactor * 0.15)) * surgeAmp;

  const minShipX = isMobile ? 55 : 85;
  const rawShipX = width * shipXRatio + forwardSurge;
  const shipX = scroll >= 0.74 ? rawShipX : Math.max(minShipX, rawShipX);

  // If ship has completely exited the screen right boundary, skip rendering
  if (shipX > width + 220) {
    return { shipX, shipY: -500, mastY: -500 };
  }

  // Wave surface tracking: elevation and derivative slope
  const surfaceY = getWaveY(shipX, time, scroll, SHIP_WAVE_LAYER, width, height, mouseY);
  const waveTilt = getWaveSlope(shipX, time, scroll, SHIP_WAVE_LAYER, width, height, mouseY);

  // Storm factors (peaks at 0.42, disappears by 0.60)
  const stormFactor = scrollMap(scroll, [
    [0.00, 0.0],
    [0.15, 0.25],
    [0.34, 0.88],
    [0.42, 1.0],
    [0.52, 0.55],
    [0.60, 0.0],
    [1.00, 0.0],
  ]);

  const heaveAmp = lerp(3.0 + stormFactor * 16.0, 1.6, calmFactor);
  const heave = Math.sin(time * (2.4 + stormFactor * 2.0 - calmFactor * 1.0)) * heaveAmp;

  const rollAmp = lerp(0.025 + stormFactor * 0.16, 0.012, calmFactor);
  const roll = Math.cos(time * (1.8 + stormFactor * 1.4 - calmFactor * 0.8)) * rollAmp;

  const shipY = surfaceY + heave - 4;
  const totalRotation = waveTilt * (0.75 + stormFactor * 0.5 - calmFactor * 0.35) + roll;

  const baseScale = isMobile ? 1.5 : 2.4;

  ctx.save();
  ctx.translate(shipX, shipY);
  ctx.rotate(totalRotation);
  ctx.scale(baseScale, baseScale);

  /* ── 1. Hydrodynamic Stern Wake ── */
  drawSternWake(ctx, stormFactor, calmFactor, time);

  /* ── 2. Heavy-Duty Steel Hull ── */
  drawHull(ctx);

  /* ── 3. Multi-Tier Superstructure, Bridge & Windows ── */
  drawSuperstructure(ctx);

  /* ── 4. Aft Working Deck & Equipment ── */
  drawAftDeck(ctx);

  /* ── 5. Lattice Mast, Radar, Strobe & Flag ── */
  drawMastAndRigging(ctx, time, stormFactor, calmFactor);

  /* ── 6. Hydrodynamic Bow Spray & Foam ── */
  drawBowSprayAndFoam(ctx, stormFactor, calmFactor, time);

  ctx.restore();

  const mastHeight = 65 * baseScale;
  return {
    shipX,
    shipY,
    mastY: shipY - mastHeight,
  };
}

/* ──────────────────────── Sub-Components ──────────────────────── */

function drawSternWake(ctx, storm, calm, time) {
  const wakeLen = lerp(lerp(120, 55, storm), 45, calm);
  const wakeSpread = lerp(lerp(16, 28, storm), 10, calm);
  const wakeAlpha = lerp(lerp(0.50, 0.20, storm), 0.24, calm);

  ctx.save();
  ctx.beginPath();
  ctx.moveTo(-25, 8);
  ctx.lineTo(-wakeLen, -wakeSpread + Math.sin(time * 3.5) * (3 * (1 - calm * 0.7)));
  ctx.lineTo(-wakeLen * 1.15, 0);
  ctx.lineTo(-wakeLen, wakeSpread + Math.sin(time * 3.5 + 1.2) * (3 * (1 - calm * 0.7)));
  ctx.closePath();

  const wakeGrad = ctx.createLinearGradient(0, 0, -wakeLen, 0);
  wakeGrad.addColorStop(0, `rgba(0, 242, 254, ${wakeAlpha})`);
  wakeGrad.addColorStop(0.3, `rgba(224, 242, 254, ${wakeAlpha * 0.8})`);
  wakeGrad.addColorStop(0.7, `rgba(186, 230, 253, ${wakeAlpha * 0.4})`);
  wakeGrad.addColorStop(1, 'rgba(0, 242, 254, 0)');

  ctx.fillStyle = wakeGrad;
  ctx.fill();

  ctx.strokeStyle = `rgba(255, 255, 255, ${0.4 * (1 - storm * 0.4) * (1 - calm * 0.4)})`;
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(-28, 4);
  ctx.lineTo(-wakeLen * 0.8, -wakeSpread * 0.6);
  ctx.moveTo(-28, 12);
  ctx.lineTo(-wakeLen * 0.8, wakeSpread * 0.6);
  ctx.stroke();

  ctx.restore();
}

function drawHull(ctx) {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(-52, 2);
  ctx.lineTo(-46, 16);
  ctx.quadraticCurveTo(-24, 25, 0, 26);
  ctx.quadraticCurveTo(28, 25, 48, 14);
  ctx.lineTo(58, -3);
  ctx.closePath();

  const bottomGrad = ctx.createLinearGradient(0, 2, 0, 26);
  bottomGrad.addColorStop(0, '#991b1b');
  bottomGrad.addColorStop(0.6, '#7f1d1d');
  bottomGrad.addColorStop(1, '#450a0a');
  ctx.fillStyle = bottomGrad;
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(-54, -2);
  ctx.lineTo(-50, 8);
  ctx.quadraticCurveTo(0, 10, 52, 6);
  ctx.lineTo(60, -5);
  ctx.quadraticCurveTo(0, -1, -54, -2);
  ctx.closePath();

  const hullGrad = ctx.createLinearGradient(0, -5, 0, 10);
  hullGrad.addColorStop(0, '#334155');
  hullGrad.addColorStop(0.5, '#1e293b');
  hullGrad.addColorStop(1, '#0f172a');
  ctx.fillStyle = hullGrad;
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(-48, 6);
  ctx.quadraticCurveTo(0, 10, 50, 5);
  ctx.strokeStyle = '#f8fafc';
  ctx.lineWidth = 1.8;
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(-47, 8);
  ctx.quadraticCurveTo(0, 12, 49, 7);
  ctx.strokeStyle = '#ef4444';
  ctx.lineWidth = 1.4;
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(-55, -2);
  ctx.lineTo(60, -5);
  ctx.strokeStyle = '#475569';
  ctx.lineWidth = 2.4;
  ctx.stroke();

  ctx.fillStyle = '#0f172a';
  ctx.beginPath();
  ctx.arc(46, 1, 2.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#94a3b8';
  ctx.lineWidth = 0.8;
  ctx.stroke();

  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(46, 1);
  ctx.lineTo(47, 6);
  ctx.stroke();

  ctx.restore();
}

function drawSuperstructure(ctx) {
  ctx.save();
  ctx.fillStyle = '#e2e8f0';
  ctx.fillRect(-18, -26, 36, 24);
  ctx.strokeStyle = '#94a3b8';
  ctx.lineWidth = 1.0;
  ctx.strokeRect(-18, -26, 36, 24);

  ctx.fillStyle = '#cbd5e1';
  ctx.fillRect(-12, -38, 28, 13);
  ctx.strokeRect(-12, -38, 28, 13);

  ctx.fillStyle = '#1e293b';
  ctx.beginPath();
  ctx.moveTo(-15, -38);
  ctx.lineTo(20, -38);
  ctx.lineTo(17, -42);
  ctx.lineTo(-14, -42);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = 'rgba(0, 242, 254, 0.9)';
  ctx.shadowColor = '#00f2fe';
  ctx.shadowBlur = 8;
  ctx.fillRect(-8, -35, 6, 6);
  ctx.fillRect(0, -35, 6, 6);
  ctx.fillRect(8, -35, 6, 6);
  ctx.fillRect(-14, -20, 5, 5);
  ctx.fillRect(-6, -20, 5, 5);
  ctx.fillRect(2, -20, 5, 5);
  ctx.fillRect(10, -20, 5, 5);
  ctx.shadowBlur = 0;

  ctx.strokeStyle = '#0f172a';
  ctx.lineWidth = 0.8;
  ctx.strokeRect(-8, -35, 6, 6);
  ctx.strokeRect(0, -35, 6, 6);
  ctx.strokeRect(8, -35, 6, 6);

  ctx.beginPath();
  ctx.arc(17, -32, 2.2, 0, Math.PI * 2);
  ctx.fillStyle = '#10b981';
  ctx.fill();
  ctx.beginPath();
  ctx.arc(-13, -32, 2.2, 0, Math.PI * 2);
  ctx.fillStyle = '#ef4444';
  ctx.fill();

  ctx.fillStyle = '#1e293b';
  ctx.beginPath();
  ctx.moveTo(-22, -18);
  ctx.lineTo(-17, -18);
  ctx.lineTo(-19, -34);
  ctx.lineTo(-24, -34);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = '#00f2fe';
  ctx.fillRect(-23, -30, 5, 3);

  ctx.fillStyle = '#f8fafc';
  ctx.fillRect(-16, -12, 8, 4);
  ctx.strokeStyle = '#f97316';
  ctx.lineWidth = 0.8;
  ctx.strokeRect(-16, -12, 8, 4);

  ctx.restore();
}

function drawAftDeck(ctx) {
  ctx.save();
  ctx.strokeStyle = '#f59e0b';
  ctx.lineWidth = 2.0;
  ctx.beginPath();
  ctx.moveTo(-44, -2);
  ctx.lineTo(-38, -26);
  ctx.lineTo(-30, -2);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(-41, -16);
  ctx.lineTo(-34, -16);
  ctx.stroke();

  ctx.fillStyle = '#334155';
  ctx.fillRect(-32, -8, 8, 6);

  ctx.strokeStyle = 'rgba(203, 213, 225, 0.6)';
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  ctx.moveTo(-54, -6);
  ctx.lineTo(-18, -6);
  ctx.moveTo(18, -6);
  ctx.lineTo(58, -8);
  ctx.stroke();

  for (let sx = -50; sx <= -22; sx += 7) {
    ctx.beginPath();
    ctx.moveTo(sx, -2);
    ctx.lineTo(sx, -6);
    ctx.stroke();
  }
  for (let sx = 22; sx <= 54; sx += 8) {
    ctx.beginPath();
    ctx.moveTo(sx, -3);
    ctx.lineTo(sx, -7);
    ctx.stroke();
  }

  ctx.beginPath();
  ctx.arc(32, -5, 3.2, 0, Math.PI * 2);
  ctx.fillStyle = '#ea580c';
  ctx.fill();
  ctx.beginPath();
  ctx.arc(32, -5, 1.4, 0, Math.PI * 2);
  ctx.fillStyle = '#334155';
  ctx.fill();

  ctx.restore();
}

function drawMastAndRigging(ctx, time, storm, calm) {
  ctx.save();
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  ctx.moveTo(0, -42);
  ctx.lineTo(0, -68);
  ctx.stroke();

  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(-11, -56);
  ctx.lineTo(11, -56);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(-7, -62);
  ctx.lineTo(7, -62);
  ctx.stroke();

  ctx.strokeStyle = 'rgba(203, 213, 225, 0.35)';
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  ctx.moveTo(0, -65);
  ctx.lineTo(-20, -38);
  ctx.moveTo(0, -65);
  ctx.lineTo(20, -38);
  ctx.stroke();

  const radarSweep = Math.cos(time * (6 - calm * 2)) * 7;
  ctx.strokeStyle = '#f8fafc';
  ctx.lineWidth = 2.0;
  ctx.beginPath();
  ctx.moveTo(-radarSweep, -58);
  ctx.lineTo(radarSweep, -58);
  ctx.stroke();

  ctx.fillStyle = '#f8fafc';
  ctx.beginPath();
  ctx.arc(-8, -45, 3.5, Math.PI, 0);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 0.6;
  ctx.stroke();

  const strobeOn = Math.sin(time * 6.5) > 0;
  ctx.beginPath();
  ctx.arc(0, -70, 3.2, 0, Math.PI * 2);
  ctx.fillStyle = strobeOn ? '#ef4444' : 'rgba(239, 68, 68, 0.2)';
  if (strobeOn) {
    ctx.shadowColor = '#ef4444';
    ctx.shadowBlur = 12;
  }
  ctx.fill();
  ctx.shadowBlur = 0;

  const flagFlutter = Math.sin(time * (5.5 + storm * 6 - calm * 2.5)) * (3.0 + storm * 4.0 - calm * 1.5);
  const flagLen = 22;

  ctx.beginPath();
  ctx.moveTo(0, -66);
  ctx.lineTo(flagLen + flagFlutter, -63);
  ctx.lineTo(0, -59);
  ctx.closePath();

  const flagGrad = ctx.createLinearGradient(0, 0, flagLen, 0);
  flagGrad.addColorStop(0, '#f59e0b');
  flagGrad.addColorStop(0.5, '#ea580c');
  flagGrad.addColorStop(1, '#0284c7');
  ctx.fillStyle = flagGrad;
  ctx.fill();

  ctx.restore();
}

function drawBowSprayAndFoam(ctx, storm, calm, time) {
  ctx.save();
  const bowSprayLen = lerp(lerp(22, 38, storm), 12, calm);
  const bowSprayHeight = lerp(lerp(8, 20, storm), 3.5, calm);

  ctx.beginPath();
  ctx.moveTo(48, 6);
  ctx.quadraticCurveTo(56, 12 + Math.sin(time * 4) * (2 * (1 - calm * 0.8)), 48 + bowSprayLen, 6 + bowSprayHeight);
  ctx.quadraticCurveTo(52, 2, 48, 6);
  ctx.fillStyle = `rgba(240, 253, 255, ${lerp(0.75 + storm * 0.2, 0.35, calm)})`;
  ctx.fill();

  if (calm < 0.6 && Math.sin(time * 5) > -0.2) {
    ctx.fillStyle = `rgba(255, 255, 255, ${0.8 * (0.6 + storm * 0.4) * (1 - calm)})`;
    for (let sp = 0; sp < (storm > 0.4 ? 8 : 4); sp++) {
      const spX = 52 + Math.random() * bowSprayLen;
      const spY = 4 - Math.random() * (bowSprayHeight * 0.9);
      ctx.beginPath();
      ctx.arc(spX, spY, 1.2 + Math.random() * 1.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  ctx.strokeStyle = `rgba(240, 250, 255, ${lerp(0.65 + storm * 0.3, 0.35, calm)})`;
  ctx.lineWidth = lerp(2.2, 1.2, calm);
  ctx.beginPath();
  ctx.moveTo(-50, 8 + Math.sin(time * 3) * (1.5 * (1 - calm * 0.7)));
  ctx.quadraticCurveTo(0, 13 + Math.cos(time * 3) * (1.5 * (1 - calm * 0.7)), 52, 7 + Math.sin(time * 3 + 1) * (1.5 * (1 - calm * 0.7)));
  ctx.stroke();

  ctx.restore();
}
