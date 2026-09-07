/**
 * drawUnderwater — Deep Underwater Research Atmosphere & Submarine Scene (75–100% Scroll).
 *
 * Components:
 * 1. Clear Deep Blue/Turquoise Oceanic Atmosphere & Sunbeams
 * 2. Floating Bioluminescent Phytoplankton Particles
 * 3. Left & Right Side Research Submersibles (AUV-01 & ROV Abyssal-02)
 */
import { scrollMap, lerp, clamp } from './types.js';

// Pre-generated Phytoplankton / Sunlit Marine Particles Pool
const PARTICLE_COUNT = 65;
const sunlitParticles = [];
for (let i = 0; i < PARTICLE_COUNT; i++) {
  sunlitParticles.push({
    x: Math.random(),
    y: Math.random(),
    r: 0.8 + Math.random() * 2.2,
    speedX: (Math.random() - 0.4) * 0.0003,
    speedY: (Math.random() - 0.6) * 0.0002,
    pulsePhase: Math.random() * Math.PI * 2,
    pulseSpeed: 0.02 + Math.random() * 0.03,
    colorType: i % 4 === 0 ? '#38bdf8' : i % 4 === 1 ? '#34d399' : i % 4 === 2 ? '#fef08a' : '#ffffff',
  });
}

// Dedicated Research Phytoplankton Particles for the Submarine Scan Beam
const BEAM_PARTICLE_COUNT = 28;
const beamPhytoplankton = [];
for (let i = 0; i < BEAM_PARTICLE_COUNT; i++) {
  beamPhytoplankton.push({
    distNorm: 0.12 + Math.random() * 0.84,
    angleOffset: (Math.random() - 0.5) * 0.88,
    r: 1.0 + Math.random() * 2.4,
    driftPhase: Math.random() * Math.PI * 2,
    driftSpeed: 0.02 + Math.random() * 0.025,
    hueType: i % 3 === 0 ? '#00f2fe' : i % 3 === 1 ? '#34d399' : '#a7f3d0',
    pulseSeed: Math.random() * 100,
  });
}

export function drawUnderwater(rc) {
  const { ctx, width, height, time, scroll, mouseX, mouseY, isMobile } = rc;

  // Scene visibility envelope: Brief pause after boat exit (scroll >= 0.79)
  const underwaterAlpha = scrollMap(scroll, [
    [0.00, 0.0],
    [0.79, 0.0],  // Wait briefly after boat exits
    [0.85, 0.55],
    [0.91, 0.98],
    [1.00, 1.0],
  ]);

  if (underwaterAlpha <= 0.01) return;

  ctx.save();

  /* ── 1. Clear Turquoise-Blue Oceanic Atmosphere ── */
  const seaGrad = ctx.createLinearGradient(0, 0, 0, height);
  seaGrad.addColorStop(0, `rgba(14, 165, 233, ${0.85 * underwaterAlpha})`);     // Vibrant azure surface
  seaGrad.addColorStop(0.25, `rgba(6, 182, 212, ${0.90 * underwaterAlpha})`);    // Turquoise mid-water
  seaGrad.addColorStop(0.65, `rgba(2, 132, 199, ${0.94 * underwaterAlpha})`);    // Deep cyan ocean
  seaGrad.addColorStop(1, `rgba(3, 45, 90, ${0.98 * underwaterAlpha})`);         // Deep navy floor
  ctx.fillStyle = seaGrad;
  ctx.fillRect(0, 0, width, height);

  /* ── 2. Realistic Sunlight Caustics & God-Rays ── */
  drawSunbeamCaustics(ctx, width, height, time, underwaterAlpha);

  /* ── 3. Floating Sunlit Phytoplankton & Micro-Bio Particles ── */
  drawPhytoplanktonParticles(ctx, width, height, time, mouseX, mouseY, underwaterAlpha, isMobile);

  /* ── 4. Submarines (Strictly on LEFT and RIGHT sides, smooth entrance from left) ── */
  const leftSubEntry = scrollMap(scroll, [
    [0.80, 0.0],
    [0.90, 1.0],
    [1.00, 1.0],
  ]);

  const subVisibility = scrollMap(scroll, [
    [0.00, 0.0],
    [0.81, 0.0],
    [0.87, 0.65],
    [0.93, 1.0],
    [1.00, 1.0],
  ]);

  if (subVisibility > 0.01) {
    // LEFT SIDE: AUV-01 "DeepSense" (Enters smoothly from the left, scaled +18%, scan beam with phytoplankton)
    drawLeftResearchSubmarine(ctx, width, height, time, mouseX, mouseY, isMobile, subVisibility, leftSubEntry);
    // RIGHT SIDE: ROV "Abyssal-02"
    drawRightResearchROV(ctx, width, height, time, mouseX, mouseY, isMobile, subVisibility);
  }

  ctx.restore();
}

/* ──────────────────────── 1. Sunbeam Caustics & Light Shafts ──────────────────────── */

function drawSunbeamCaustics(ctx, width, height, time, alpha) {
  ctx.save();
  const rayCount = 7;

  for (let r = 0; r < rayCount; r++) {
    const rayX = width * (0.10 + r * 0.14) + Math.sin(time * 0.5 + r * 1.2) * 40;
    const rayTopW = 25 + r * 10;
    const rayBotW = 120 + r * 35;
    const rayAlpha = (0.12 + Math.sin(time * 0.9 + r * 1.7) * 0.04) * alpha;

    const rayGrad = ctx.createLinearGradient(rayX, 0, rayX + 90, height * 0.85);
    rayGrad.addColorStop(0, `rgba(255, 255, 255, ${rayAlpha * 2.2})`);
    rayGrad.addColorStop(0.3, `rgba(186, 230, 253, ${rayAlpha * 1.5})`);
    rayGrad.addColorStop(0.7, `rgba(6, 182, 212, ${rayAlpha * 0.6})`);
    rayGrad.addColorStop(1, 'transparent');

    ctx.beginPath();
    ctx.moveTo(rayX - rayTopW / 2, 0);
    ctx.lineTo(rayX + rayTopW / 2, 0);
    ctx.lineTo(rayX + 90 + rayBotW / 2, height * 0.85);
    ctx.lineTo(rayX + 90 - rayBotW / 2, height * 0.85);
    ctx.closePath();
    ctx.fillStyle = rayGrad;
    ctx.fill();
  }

  // Surface water caustic mesh ripples
  ctx.strokeStyle = `rgba(255, 255, 255, ${0.15 * alpha})`;
  ctx.lineWidth = 1.2;
  for (let i = 0; i < 4; i++) {
    const cy = 15 + i * 20 + Math.sin(time * 1.5 + i) * 6;
    ctx.beginPath();
    ctx.moveTo(0, cy);
    for (let x = 0; x <= width; x += 40) {
      const ny = cy + Math.sin(x * 0.015 + time * 2 + i) * 6 + Math.cos(x * 0.03 - time) * 3;
      ctx.lineTo(x, ny);
    }
    ctx.stroke();
  }

  ctx.restore();
}

/* ──────────────────────── 2. Floating Sunlit Phytoplankton Particles ──────────────────────── */

function drawPhytoplanktonParticles(ctx, width, height, time, mouseX, mouseY, alpha, isMobile) {
  ctx.save();
  const count = isMobile ? 30 : PARTICLE_COUNT;

  for (let i = 0; i < count; i++) {
    const p = sunlitParticles[i];
    p.x = (p.x + p.speedX + 1) % 1;
    p.y = (p.y + p.speedY + 1) % 1;
    p.pulsePhase += p.pulseSpeed;

    const px = p.x * width + mouseX * 14;
    const py = p.y * height + mouseY * 10;
    const glow = (0.5 + 0.5 * Math.sin(p.pulsePhase)) * alpha;

    ctx.beginPath();
    ctx.arc(px, py, p.r, 0, Math.PI * 2);
    ctx.fillStyle = p.colorType;
    ctx.globalAlpha = 0.85 * glow;
    if (!isMobile) {
      ctx.shadowColor = p.colorType;
      ctx.shadowBlur = 4;
    }
    ctx.fill();
    if (!isMobile) {
      ctx.shadowBlur = 0;
    }
  }

  ctx.restore();
}

/* ──────────────────────── 3. Submarine LEFT: AUV-01 "DeepSense" ──────────────────────── */

function drawLeftResearchSubmarine(ctx, width, height, time, mouseX, mouseY, isMobile, alpha, entryProgress = 1.0) {
  // Proportional scale increase (~15–20%)
  const scale = isMobile ? 1.12 : 1.60;

  // Smooth entrance from the left, keeping it strictly on the left flank
  const easedEntry = 1 - Math.pow(1 - entryProgress, 3);
  const startX = -180 * scale;
  const restX = width * (isMobile ? 0.16 : 0.13) + mouseX * 10 + Math.sin(time * 0.4) * 8;
  const subX = lerp(startX, restX, easedEntry);

  const subBob = Math.sin(time * 0.9) * 8;
  const subPitch = Math.cos(time * 0.9) * 0.03 + 0.02;
  const subY = height * 0.44 + subBob + mouseY * 10;

  ctx.save();
  ctx.translate(subX, subY);
  ctx.rotate(subPitch);
  ctx.scale(scale, scale);

  /* Enhanced High-Visibility Forward Fluorometer / Scanning Beam */
  const beamAngle = Math.sin(time * 1.2) * 0.08 + 0.22;
  const beamLen = isMobile ? 240 : 360;
  const beamSpread = 0.35;

  ctx.save();
  const beamOriginX = 54;
  const beamOriginY = 4;

  const bx1 = beamOriginX + Math.cos(beamAngle - beamSpread) * beamLen;
  const by1 = beamOriginY + Math.sin(beamAngle - beamSpread) * beamLen;
  const bx2 = beamOriginX + Math.cos(beamAngle + beamSpread) * beamLen;
  const by2 = beamOriginY + Math.sin(beamAngle + beamSpread) * beamLen;

  // 1. Broad atmospheric projection wash
  const scanGrad = ctx.createRadialGradient(beamOriginX, beamOriginY, 4, beamOriginX, beamOriginY, beamLen);
  scanGrad.addColorStop(0, `rgba(0, 242, 254, ${0.75 * alpha})`);
  scanGrad.addColorStop(0.25, `rgba(56, 189, 248, ${0.45 * alpha})`);
  scanGrad.addColorStop(0.65, `rgba(16, 185, 129, ${0.22 * alpha})`);
  scanGrad.addColorStop(1, 'transparent');

  ctx.beginPath();
  ctx.moveTo(beamOriginX, beamOriginY);
  ctx.lineTo(bx1, by1);
  ctx.lineTo(bx2, by2);
  ctx.closePath();
  ctx.fillStyle = scanGrad;
  ctx.fill();

  // 2. High-intensity narrow central core beam
  const coreSpread = 0.12;
  const cx1 = beamOriginX + Math.cos(beamAngle - coreSpread) * beamLen * 0.9;
  const cy1 = beamOriginY + Math.sin(beamAngle - coreSpread) * beamLen * 0.9;
  const cx2 = beamOriginX + Math.cos(beamAngle + coreSpread) * beamLen * 0.9;
  const cy2 = beamOriginY + Math.sin(beamAngle + coreSpread) * beamLen * 0.9;

  const coreGrad = ctx.createRadialGradient(beamOriginX, beamOriginY, 2, beamOriginX, beamOriginY, beamLen * 0.85);
  coreGrad.addColorStop(0, `rgba(224, 242, 254, ${0.85 * alpha})`);
  coreGrad.addColorStop(0.3, `rgba(0, 242, 254, ${0.55 * alpha})`);
  coreGrad.addColorStop(1, 'transparent');

  ctx.beginPath();
  ctx.moveTo(beamOriginX, beamOriginY);
  ctx.lineTo(cx1, cy1);
  ctx.lineTo(cx2, cy2);
  ctx.closePath();
  ctx.fillStyle = coreGrad;
  ctx.fill();

  // 3. Scanning LiDAR pulse waves traveling down the beam
  for (let p = 0; p < 2; p++) {
    const scanPulse = (time * 0.75 + p * 0.5) % 1.0;
    const spX1 = lerp(beamOriginX, bx1, scanPulse);
    const spY1 = lerp(beamOriginY, by1, scanPulse);
    const spX2 = lerp(beamOriginX, bx2, scanPulse);
    const spY2 = lerp(beamOriginY, by2, scanPulse);

    ctx.beginPath();
    ctx.moveTo(spX1, spY1);
    ctx.lineTo(spX2, spY2);
    ctx.strokeStyle = `rgba(52, 211, 153, ${0.80 * alpha * (1 - scanPulse)})`;
    ctx.lineWidth = 2.0;
    ctx.stroke();
  }

  // 4. Subtle concentration of glowing phytoplankton INSIDE the beam, reacting to the scan
  for (let i = 0; i < beamPhytoplankton.length; i++) {
    const bp = beamPhytoplankton[i];
    const dist = bp.distNorm * beamLen;
    const angle = beamAngle + bp.angleOffset * beamSpread;

    // Subtle micro-excitation & fluid reaction as the beam passes through
    const reactJitterX = Math.sin(time * 12 + bp.pulseSeed) * 1.8;
    const reactJitterY = Math.cos(time * 15 + bp.pulseSeed) * 1.5;
    const driftOffset = Math.sin(time * 0.8 + bp.driftPhase) * 6;

    const px = beamOriginX + Math.cos(angle) * dist + reactJitterX - driftOffset;
    const py = beamOriginY + Math.sin(angle) * dist + reactJitterY;

    // Bio-excitation glow inside beam
    const pulseGlow = (0.7 + 0.3 * Math.sin(time * 4 + bp.pulseSeed)) * alpha;

    ctx.beginPath();
    ctx.arc(px, py, bp.r, 0, Math.PI * 2);
    ctx.fillStyle = bp.hueType;
    if (!isMobile) {
      ctx.shadowColor = bp.hueType;
      ctx.shadowBlur = 5;
    }
    ctx.globalAlpha = pulseGlow;
    ctx.fill();
    if (!isMobile) {
      ctx.shadowBlur = 0;
    }

    // Core bio-luminescent specular center
    ctx.beginPath();
    ctx.arc(px, py, bp.r * 0.45, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff';
    ctx.fill();

    // Detection reticle ring on key specimens
    if (i % 4 === 0) {
      ctx.beginPath();
      ctx.arc(px, py, bp.r * 2.6, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(0, 242, 254, ${0.55 * pulseGlow})`;
      ctx.lineWidth = 0.8;
      ctx.stroke();
    }
  }
  ctx.shadowBlur = 0;
  ctx.globalAlpha = 1.0;
  ctx.restore();

  /* Submarine Hull */
  const propSpin = Math.sin(time * 25) * 8;
  ctx.save();
  ctx.fillStyle = '#64748b';
  ctx.fillRect(-62, -2, 6, 4);
  ctx.strokeStyle = '#94a3b8';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(-62, -propSpin);
  ctx.lineTo(-62, propSpin);
  ctx.stroke();
  ctx.restore();

  ctx.beginPath();
  ctx.moveTo(-56, 0);
  ctx.quadraticCurveTo(-35, -20, 10, -20);
  ctx.quadraticCurveTo(48, -18, 56, 0);
  ctx.quadraticCurveTo(48, 20, 10, 20);
  ctx.quadraticCurveTo(-35, 20, -56, 0);
  ctx.closePath();

  const hullGrad = ctx.createLinearGradient(0, -20, 0, 20);
  hullGrad.addColorStop(0, '#1e293b');
  hullGrad.addColorStop(0.3, '#334155');
  hullGrad.addColorStop(0.7, '#0f172a');
  hullGrad.addColorStop(1, '#020617');
  ctx.fillStyle = hullGrad;
  ctx.fill();
  ctx.strokeStyle = '#00f2fe';
  ctx.lineWidth = 1.4;
  ctx.stroke();

  // Conning Tower & Mast
  ctx.fillStyle = '#1e293b';
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.roundRect(-8, -32, 22, 14, 4);
  ctx.fill();
  ctx.stroke();

  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(4, -32);
  ctx.lineTo(4, -44);
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(4, -46, 2.5, 0, Math.PI * 2);
  ctx.fillStyle = '#34d399';
  ctx.shadowColor = '#10b981';
  ctx.shadowBlur = 8;
  ctx.fill();
  ctx.shadowBlur = 0;

  // Luminous Viewport Dome
  ctx.beginPath();
  ctx.arc(44, 0, 10, -Math.PI / 2, Math.PI / 2);
  ctx.fillStyle = 'rgba(0, 242, 254, 0.85)';
  ctx.shadowColor = '#00f2fe';
  ctx.shadowBlur = 14;
  ctx.fill();
  ctx.strokeStyle = '#e0f2fe';
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ctx.shadowBlur = 0;

  // Stabilizer Fin
  ctx.fillStyle = '#0f172a';
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 1.0;
  ctx.beginPath();
  ctx.moveTo(12, 14);
  ctx.lineTo(26, 22);
  ctx.lineTo(8, 22);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Safety Orange Stripe
  ctx.strokeStyle = '#f59e0b';
  ctx.lineWidth = 2.0;
  ctx.beginPath();
  ctx.moveTo(-45, 6);
  ctx.quadraticCurveTo(0, 8, 40, 5);
  ctx.stroke();

  ctx.restore();

  /* Left Side HUD Badge (Fades in smoothly as submarine enters) */
  if (entryProgress > 0.3) {
    const hudAlpha = scrollMap(entryProgress, [[0.3, 0], [0.75, 1]]) * alpha;
    ctx.save();
    const hudX = subX + (isMobile ? 10 : 105);
    const hudY = subY - (isMobile ? 75 : 68);
    ctx.translate(hudX, hudY);

    const badgeW = isMobile ? 180 : 215;
    const badgeH = 42;
    ctx.fillStyle = `rgba(2, 14, 30, ${0.85 * hudAlpha})`;
    ctx.strokeStyle = `rgba(52, 211, 153, ${0.75 * hudAlpha})`;
    ctx.lineWidth = 1.2;
    ctx.shadowColor = '#10b981';
    ctx.shadowBlur = 10;

    ctx.beginPath();
    ctx.roundRect(-badgeW / 2, -badgeH / 2, badgeW, badgeH, 8);
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;

    ctx.font = 'bold 9px monospace';
    ctx.fillStyle = `rgba(52, 211, 153, ${hudAlpha})`;
    ctx.textAlign = 'left';
    ctx.fillText('● AUV-01 // BIO-FLUOROMETER', -badgeW / 2 + 8, -badgeH / 2 + 13);

    ctx.font = '8.5px monospace';
    ctx.fillStyle = `rgba(224, 242, 254, ${0.9 * hudAlpha})`;
    ctx.fillText('SCAN BEAM: ACTIVE [480nm]', -badgeW / 2 + 8, -badgeH / 2 + 25);
    ctx.fillStyle = `rgba(0, 242, 254, ${0.85 * hudAlpha})`;
    ctx.fillText('PHYTOPLANKTON: DETECTED (HIGH)', -badgeW / 2 + 8, -badgeH / 2 + 35);

    ctx.restore();
  }
}

/* ──────────────────────── 4. Submarine RIGHT: ROV "Abyssal-02" ──────────────────────── */

function drawRightResearchROV(ctx, width, height, time, mouseX, mouseY, isMobile, alpha) {
  const rovBob = Math.sin(time * 1.1 + 1.5) * 7;
  const rovPitch = -Math.cos(time * 0.8) * 0.03 - 0.01;

  const rovX = width * (isMobile ? 0.82 : 0.85) + mouseX * 14 + Math.cos(time * 0.4) * 12;
  const rovY = height * 0.58 + rovBob + mouseY * 12;
  const scale = isMobile ? 0.75 : 1.05;

  ctx.save();
  ctx.translate(rovX, rovY);
  ctx.rotate(rovPitch);
  ctx.scale(scale, scale);

  /* Dual Floodlights Piercing Clear Water */
  ctx.save();
  const floodGrad = ctx.createRadialGradient(-30, 0, 4, -180, 20, 180);
  floodGrad.addColorStop(0, `rgba(255, 255, 255, ${0.75 * alpha})`);
  floodGrad.addColorStop(0.3, `rgba(0, 242, 254, ${0.45 * alpha})`);
  floodGrad.addColorStop(0.8, `rgba(6, 182, 212, ${0.12 * alpha})`);
  floodGrad.addColorStop(1, 'transparent');

  ctx.beginPath();
  ctx.moveTo(-28, -8);
  ctx.lineTo(-190, -45);
  ctx.lineTo(-170, 75);
  ctx.lineTo(-28, 12);
  ctx.closePath();
  ctx.fillStyle = floodGrad;
  ctx.fill();
  ctx.restore();

  // Tether Cable
  ctx.strokeStyle = `rgba(245, 158, 11, ${0.7 * alpha})`;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(18, -14);
  ctx.quadraticCurveTo(60, -80, 120, -180);
  ctx.stroke();

  // Chassis
  ctx.fillStyle = '#0f172a';
  ctx.strokeStyle = '#f59e0b';
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.roundRect(-32, -18, 54, 36, 6);
  ctx.fill();
  ctx.stroke();

  ctx.fillStyle = '#1e293b';
  ctx.beginPath();
  ctx.arc(-4, 0, 12, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 1.2;
  ctx.stroke();

  // Camera & Light Ring
  ctx.beginPath();
  ctx.arc(-26, -2, 5.5, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(0, 242, 254, 0.9)';
  ctx.shadowColor = '#00f2fe';
  ctx.shadowBlur = 12;
  ctx.fill();
  ctx.shadowBlur = 0;

  // Robotic Arm
  ctx.strokeStyle = '#94a3b8';
  ctx.lineWidth = 2.0;
  ctx.beginPath();
  ctx.moveTo(-18, 14);
  ctx.lineTo(-34, 24);
  ctx.lineTo(-44, 18);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(-44, 15);
  ctx.lineTo(-50, 16);
  ctx.moveTo(-44, 21);
  ctx.lineTo(-50, 20);
  ctx.stroke();

  ctx.fillStyle = '#334155';
  ctx.fillRect(8, -24, 14, 6);
  ctx.fillRect(8, 18, 14, 6);

  ctx.restore();

  /* Right Side HUD Telemetry */
  ctx.save();
  ctx.translate(rovX - (isMobile ? 40 : 60), rovY + 45);
  ctx.fillStyle = `rgba(2, 14, 30, ${0.85 * alpha})`;
  ctx.strokeStyle = `rgba(0, 242, 254, ${0.65 * alpha})`;
  ctx.lineWidth = 1.0;
  ctx.beginPath();
  ctx.roundRect(-75, -15, 150, 30, 6);
  ctx.fill();
  ctx.stroke();

  ctx.font = '8.5px monospace';
  ctx.fillStyle = `rgba(0, 242, 254, ${alpha})`;
  ctx.textAlign = 'center';
  ctx.fillText('ROV-02 // REEF BIO-SCAN', 0, -3);
  ctx.fillStyle = `rgba(148, 163, 184, ${alpha})`;
  ctx.fillText('HABITAT STABLE', 0, 9);
  ctx.restore();
}
