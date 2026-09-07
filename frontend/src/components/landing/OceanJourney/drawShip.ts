/**
 * drawShip — Large Cinematic Marine Research Vessel (2.5× Scale) with
 * complete 5-stage scroll story:
 * 1. 0–30%: Cruises at starting center position (0.50)
 * 2. 30–60%: Smoothly travels to far-left edge (0.09) as storm builds
 * 3. 60–75%: Holds far-left position (0.09) under satellite rescue laser
 * 4. 75–85%: Weather recovers, skies clear, vessel stabilizes
 * 5. 85–100%: Drifts gracefully across calm seas toward the safe haven lighthouse (0.72)
 */
import {
  RenderContext,
  scrollMap,
  lerp,
  SHIP_WAVE_LAYER,
} from './types';
import { getWaveY, getWaveSlope } from './drawWaves';

export function drawShip(rc: RenderContext): { shipX: number; shipY: number; mastY: number } {
  const { ctx, width, height, time, scroll, mouseY, isMobile } = rc;

  // Horizontal position timeline across the entire journey:
  // 0–30%: Center (0.50)
  // 30–60%: Far-left translation (0.50 -> 0.09)
  // 60–75%: Far-left hold during storm & satellite lock (0.09)
  // 75–85%: Weather clears, vessel stabilizes (0.09 -> 0.12)
  // 85–100%: Smooth drift & deceleration toward the safe harbor lighthouse (0.12 -> 0.72)
  const shipXRatio = scrollMap(scroll, [
    [0.00, 0.50],
    [0.30, 0.50],
    [0.60, 0.09],
    [0.75, 0.09],
    [0.85, 0.12],
    [0.92, 0.45],
    [0.97, 0.65],
    [1.00, 0.72],
  ]);

  // Peaceful calm factor as ship approaches the lighthouse (0.80 - 1.00)
  const calmFactor = scrollMap(scroll, [
    [0.00, 0.0],
    [0.75, 0.0],
    [0.85, 0.4],
    [1.00, 1.0],
  ]);

  // Natural forward cruising surge (slows down as vessel anchors near lighthouse)
  const surgeAmp = lerp(8, 2.5, calmFactor);
  const forwardSurge = Math.sin(time * (0.4 - calmFactor * 0.15)) * surgeAmp;

  const minShipX = isMobile ? 55 : 85;
  const maxShipX = width * 0.78;
  const rawShipX = width * shipXRatio + forwardSurge;
  const shipX = Math.min(maxShipX, Math.max(minShipX, rawShipX));

  // Wave surface tracking: elevation and derivative slope
  const surfaceY = getWaveY(shipX, time, scroll, SHIP_WAVE_LAYER, width, height, mouseY);
  const waveTilt = getWaveSlope(shipX, time, scroll, SHIP_WAVE_LAYER, width, height, mouseY);

  // Storm factors (peaks at 0.55, disappears by 0.80)
  const stormFactor = scrollMap(scroll, [
    [0.00, 0.0],
    [0.20, 0.25],
    [0.45, 0.88],
    [0.55, 1.0],
    [0.68, 0.55],
    [0.78, 0.12],
    [0.85, 0.0],
    [1.00, 0.0],
  ]);

  // Dynamic heave (up/down) and pitch/roll moments (gentle and smooth near lighthouse)
  const heaveAmp = lerp(3.0 + stormFactor * 16.0, 1.6, calmFactor);
  const heave = Math.sin(time * (2.4 + stormFactor * 2.0 - calmFactor * 1.0)) * heaveAmp;

  const rollAmp = lerp(0.025 + stormFactor * 0.16, 0.012, calmFactor);
  const roll = Math.cos(time * (1.8 + stormFactor * 1.4 - calmFactor * 0.8)) * rollAmp;

  // Ship physically rests ON the wave surface
  const shipY = surfaceY + heave - 4;
  const totalRotation = waveTilt * (0.75 + stormFactor * 0.5 - calmFactor * 0.35) + roll;

  // 2.4× Scale for Large Cinematic Vessel
  const baseScale = isMobile ? 1.5 : 2.4;

  ctx.save();
  ctx.translate(shipX, shipY);
  ctx.rotate(totalRotation);
  ctx.scale(baseScale, baseScale);

  /* ── 1. Large Hydrodynamic Stern Wake ── */
  drawSternWake(ctx, stormFactor, calmFactor, time);

  /* ── 2. Heavy-Duty Steel Hull ── */
  drawHull(ctx);

  /* ── 3. Multi-Tier Superstructure, Bridge & Windows ── */
  drawSuperstructure(ctx);

  /* ── 4. Aft Working Deck, Gantry Crane & Details ── */
  drawAftDeck(ctx);

  /* ── 5. Lattice Mast, Radar Scanner, Strobe & Fluttering Flag ── */
  drawMastAndRigging(ctx, time, stormFactor, calmFactor);

  /* ── 6. Hydrodynamic Bow Spray & Waterline Foam Collar ── */
  drawBowSprayAndFoam(ctx, stormFactor, calmFactor, time);

  ctx.restore();

  // Return masthead coordinates for Satellite targeting laser beam
  const mastHeight = 65 * baseScale;
  return {
    shipX,
    shipY,
    mastY: shipY - mastHeight,
  };
}

/* ──────────────────────── Sub-Components ──────────────────────── */

/* ── 1. Stern Wake ── */
function drawSternWake(ctx: CanvasRenderingContext2D, storm: number, calm: number, time: number): void {
  const wakeLen = lerp(lerp(120, 55, storm), 38, calm);
  const wakeSpread = lerp(lerp(16, 28, storm), 9, calm);
  const wakeAlpha = lerp(lerp(0.50, 0.20, storm), 0.22, calm);

  ctx.save();

  // Expanding Twin-Propeller Turbulent Wake
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

  // Propeller Foam Trails
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

/* ── 2. Steel Hull ── */
function drawHull(ctx: CanvasRenderingContext2D): void {
  ctx.save();

  // Lower Hull / Crimson Anti-Fouling Keel
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

  // Upper Main Hull Plates (Marine Charcoal / Navy Steel)
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

  // White Waterline Boot-Topping Stripe
  ctx.beginPath();
  ctx.moveTo(-48, 6);
  ctx.quadraticCurveTo(0, 10, 50, 5);
  ctx.strokeStyle = '#f8fafc';
  ctx.lineWidth = 1.8;
  ctx.stroke();

  // Crimson Accent Stripe
  ctx.beginPath();
  ctx.moveTo(-47, 8);
  ctx.quadraticCurveTo(0, 12, 49, 7);
  ctx.strokeStyle = '#ef4444';
  ctx.lineWidth = 1.4;
  ctx.stroke();

  // Gunwale / Bulwark Railing Plate
  ctx.beginPath();
  ctx.moveTo(-55, -2);
  ctx.lineTo(60, -5);
  ctx.strokeStyle = '#475569';
  ctx.lineWidth = 2.4;
  ctx.stroke();

  // Hawsehole & Hanging Steel Anchor
  ctx.fillStyle = '#0f172a';
  ctx.beginPath();
  ctx.arc(46, 1, 2.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#94a3b8';
  ctx.lineWidth = 0.8;
  ctx.stroke();

  // Anchor Shank & Flukes
  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(46, 1);
  ctx.lineTo(47, 6);
  ctx.stroke();

  ctx.restore();
}

/* ── 3. Superstructure & Bridge ── */
function drawSuperstructure(ctx: CanvasRenderingContext2D): void {
  ctx.save();

  // Main Deckhouse Structure (Two-tier)
  ctx.fillStyle = '#e2e8f0';
  ctx.fillRect(-18, -26, 36, 24);
  ctx.strokeStyle = '#94a3b8';
  ctx.lineWidth = 1.0;
  ctx.strokeRect(-18, -26, 36, 24);

  // Upper Navigation Bridge Tier
  ctx.fillStyle = '#cbd5e1';
  ctx.fillRect(-12, -38, 28, 13);
  ctx.strokeRect(-12, -38, 28, 13);

  // Slanted Fore Bridge Visor / Roof
  ctx.fillStyle = '#1e293b';
  ctx.beginPath();
  ctx.moveTo(-15, -38);
  ctx.lineTo(20, -38);
  ctx.lineTo(17, -42);
  ctx.lineTo(-14, -42);
  ctx.closePath();
  ctx.fill();

  // Bridge Windows with Electric Cyan Intelligence Glow
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

  // Window Frames
  ctx.strokeStyle = '#0f172a';
  ctx.lineWidth = 0.8;
  ctx.strokeRect(-8, -35, 6, 6);
  ctx.strokeRect(0, -35, 6, 6);
  ctx.strokeRect(8, -35, 6, 6);

  // Navigation Lanterns (Starboard Green, Port Red)
  ctx.beginPath();
  ctx.arc(17, -32, 2.2, 0, Math.PI * 2);
  ctx.fillStyle = '#10b981';
  ctx.fill();
  ctx.beginPath();
  ctx.arc(-13, -32, 2.2, 0, Math.PI * 2);
  ctx.fillStyle = '#ef4444';
  ctx.fill();

  // Exhaust Funnel Stack with ORCA Navy / Cyan Band
  ctx.fillStyle = '#1e293b';
  ctx.beginPath();
  ctx.moveTo(-22, -18);
  ctx.lineTo(-17, -18);
  ctx.lineTo(-19, -34);
  ctx.lineTo(-24, -34);
  ctx.closePath();
  ctx.fill();

  // Funnel Cyan Stripe
  ctx.fillStyle = '#00f2fe';
  ctx.fillRect(-23, -30, 5, 3);

  // White Life-Raft Container Pods
  ctx.fillStyle = '#f8fafc';
  ctx.fillRect(-16, -12, 8, 4);
  ctx.strokeStyle = '#f97316';
  ctx.lineWidth = 0.8;
  ctx.strokeRect(-16, -12, 8, 4);

  ctx.restore();
}

/* ── 4. Aft Working Deck & Equipment ── */
function drawAftDeck(ctx: CanvasRenderingContext2D): void {
  ctx.save();

  // A-Frame Oceanographic Derrick Gantry on Stern
  ctx.strokeStyle = '#f59e0b';
  ctx.lineWidth = 2.0;
  ctx.beginPath();
  ctx.moveTo(-44, -2);
  ctx.lineTo(-38, -26);
  ctx.lineTo(-30, -2);
  ctx.stroke();

  // Gantry Crossbar
  ctx.beginPath();
  ctx.moveTo(-41, -16);
  ctx.lineTo(-34, -16);
  ctx.stroke();

  // Deck Winch Drum
  ctx.fillStyle = '#334155';
  ctx.fillRect(-32, -8, 8, 6);

  // Safety Lifeline Railing along Gunwale
  ctx.strokeStyle = 'rgba(203, 213, 225, 0.6)';
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  ctx.moveTo(-54, -6);
  ctx.lineTo(-18, -6);
  ctx.moveTo(18, -6);
  ctx.lineTo(58, -8);
  ctx.stroke();

  // Railing Stanchions
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

  // Orange Lifebuoy Ring on Railing
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

/* ── 5. Mast, Radar, Strobe & Flag ── */
function drawMastAndRigging(ctx: CanvasRenderingContext2D, time: number, storm: number, calm: number): void {
  ctx.save();

  // Main Lattice Mast Spar
  ctx.strokeStyle = '#1e293b';
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  ctx.moveTo(0, -42);
  ctx.lineTo(0, -68);
  ctx.stroke();

  // Radar Yardarm Crossbars
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(-11, -56);
  ctx.lineTo(11, -56);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(-7, -62);
  ctx.lineTo(7, -62);
  ctx.stroke();

  // Rigging Stay Lines
  ctx.strokeStyle = 'rgba(203, 213, 225, 0.35)';
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  ctx.moveTo(0, -65);
  ctx.lineTo(-20, -38);
  ctx.moveTo(0, -65);
  ctx.lineTo(20, -38);
  ctx.stroke();

  // Revolving Open-Array Radar Scanner
  const radarSweep = Math.cos(time * (6 - calm * 2)) * 7;
  ctx.strokeStyle = '#f8fafc';
  ctx.lineWidth = 2.0;
  ctx.beginPath();
  ctx.moveTo(-radarSweep, -58);
  ctx.lineTo(radarSweep, -58);
  ctx.stroke();

  // Satellite Dome (Radome)
  ctx.fillStyle = '#f8fafc';
  ctx.beginPath();
  ctx.arc(-8, -45, 3.5, Math.PI, 0);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 0.6;
  ctx.stroke();

  // Masthead Pulsing High-Intensity Safety Strobe
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

  // Large Fluttering Fleet Flag
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

/* ── 6. Hydrodynamic Bow Spray & Hull Waterline Foam ── */
function drawBowSprayAndFoam(ctx: CanvasRenderingContext2D, storm: number, calm: number, time: number): void {
  ctx.save();

  // Dynamic V-Shaped Bow Wave Slicing Water (gentle ripples near lighthouse)
  const bowSprayLen = lerp(lerp(22, 38, storm), 8, calm);
  const bowSprayHeight = lerp(lerp(8, 20, storm), 2.5, calm);

  ctx.beginPath();
  ctx.moveTo(48, 6);
  ctx.quadraticCurveTo(56, 12 + Math.sin(time * 4) * (2 * (1 - calm * 0.8)), 48 + bowSprayLen, 6 + bowSprayHeight);
  ctx.quadraticCurveTo(52, 2, 48, 6);
  ctx.fillStyle = `rgba(240, 253, 255, ${lerp(0.75 + storm * 0.2, 0.35, calm)})`;
  ctx.fill();

  // Leaping Bow Spray Particles (vanish in calm waters)
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

  // Waterline Disturbance Foam Hugging the Hull
  ctx.strokeStyle = `rgba(240, 250, 255, ${lerp(0.65 + storm * 0.3, 0.35, calm)})`;
  ctx.lineWidth = lerp(2.2, 1.2, calm);
  ctx.beginPath();
  ctx.moveTo(-50, 8 + Math.sin(time * 3) * (1.5 * (1 - calm * 0.7)));
  ctx.quadraticCurveTo(0, 13 + Math.cos(time * 3) * (1.5 * (1 - calm * 0.7)), 52, 7 + Math.sin(time * 3 + 1) * (1.5 * (1 - calm * 0.7)));
  ctx.stroke();

  ctx.restore();
}
