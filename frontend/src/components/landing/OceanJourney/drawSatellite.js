/**
 * drawSatellite — High-orbit ORCA satellite positioned at the FAR-RIGHT EDGE,
 * active during storm & rescue phases (22–65% scroll), connecting a pulsing cyan
 * telemetry beam to the vessel on the left, fading as skies clear into dawn.
 */
import { scrollMap, lerp } from './types.js';

export function drawSatellite(rc, targetShip) {
  const { ctx, width, height, time, scroll, mouseX, isMobile } = rc;

  // Satellite visibility envelope (compressed to 22–65%):
  const satVisibility = scrollMap(scroll, [
    [0.00, 0.0],
    [0.22, 0.0],
    [0.34, 1.0],
    [0.56, 1.0],
    [0.64, 0.3],
    [0.70, 0.0],
  ]);

  if (satVisibility <= 0.01) return;

  const satXRatio = scrollMap(scroll, [
    [0.00, 0.95],
    [0.22, 0.95],
    [0.34, 0.90],
    [1.00, 0.90],
  ]);

  const maxSatX = isMobile ? width - 50 : width - 75;
  const satX = Math.min(maxSatX, width * satXRatio + mouseX * 15 + Math.sin(time * 0.3) * 6);
  const satY = height * 0.14 + Math.cos(time * 0.25) * 5;

  ctx.save();

  /* ── 1. Pulsing Signal Beam Connecting Far-Right Satellite to Left Ship ── */
  const beamIntensity = scrollMap(scroll, [
    [0.00, 0.0],
    [0.24, 0.0],
    [0.34, 0.9],
    [0.45, 1.0],
    [0.56, 0.8],
    [0.62, 0.0],
  ]);

  if (beamIntensity > 0.02) {
    const startX = satX;
    const startY = satY + 10;
    const endX = targetShip.shipX;
    const endY = targetShip.mastY;

    // Outer Cone Beam Haze
    const coneGrad = ctx.createLinearGradient(startX, startY, endX, endY);
    coneGrad.addColorStop(0, `rgba(0, 242, 254, ${0.45 * beamIntensity * satVisibility})`);
    coneGrad.addColorStop(0.5, `rgba(6, 182, 212, ${0.25 * beamIntensity * satVisibility})`);
    coneGrad.addColorStop(1, `rgba(0, 242, 254, ${0.55 * beamIntensity * satVisibility})`);

    ctx.beginPath();
    ctx.moveTo(startX - 8, startY);
    ctx.lineTo(endX - 30, endY);
    ctx.lineTo(endX + 30, endY);
    ctx.lineTo(startX + 8, startY);
    ctx.closePath();
    ctx.fillStyle = coneGrad;
    ctx.fill();

    // Sharp Core Laser Line
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.strokeStyle = `rgba(220, 250, 255, ${0.95 * beamIntensity * satVisibility})`;
    ctx.lineWidth = 2.8;
    ctx.shadowColor = '#00f2fe';
    ctx.shadowBlur = 18;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Animated Traveling Telemetry Signal Pulses
    const pulseCount = 5;
    for (let p = 0; p < pulseCount; p++) {
      const pulseT = ((time * 0.85 + p / pulseCount) % 1.0);
      const px = lerp(startX, endX, pulseT);
      const py = lerp(startY, endY, pulseT);
      const ringRadius = lerp(5, 34, pulseT);
      const ringAlpha = Math.sin(pulseT * Math.PI) * beamIntensity * satVisibility * 0.85;

      ctx.beginPath();
      ctx.ellipse(px, py, ringRadius, ringRadius * 0.45, 0, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(0, 242, 254, ${ringAlpha})`;
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }

    // Ship Target Lock Reticle
    const lockPulse = 1 + Math.sin(time * 6) * 0.15;
    ctx.save();
    ctx.translate(endX, endY);
    ctx.beginPath();
    ctx.arc(0, 0, 26 * lockPulse, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(0, 242, 254, ${0.85 * beamIntensity * satVisibility})`;
    ctx.lineWidth = 2.0;
    ctx.setLineDash([4, 4]);
    ctx.stroke();

    ctx.setLineDash([]);
    ctx.strokeStyle = `rgba(0, 242, 254, ${0.9 * beamIntensity * satVisibility})`;
    ctx.beginPath();
    ctx.moveTo(-32 * lockPulse, 0);
    ctx.lineTo(-16 * lockPulse, 0);
    ctx.moveTo(16 * lockPulse, 0);
    ctx.lineTo(32 * lockPulse, 0);
    ctx.moveTo(0, -32 * lockPulse);
    ctx.lineTo(0, -16 * lockPulse);
    ctx.moveTo(0, 16 * lockPulse);
    ctx.lineTo(0, 32 * lockPulse);
    ctx.stroke();

    const deckAura = ctx.createRadialGradient(0, 10, 2, 0, 10, 55);
    deckAura.addColorStop(0, `rgba(0, 242, 254, ${0.75 * beamIntensity * satVisibility})`);
    deckAura.addColorStop(0.5, `rgba(0, 242, 254, ${0.25 * beamIntensity * satVisibility})`);
    deckAura.addColorStop(1, 'transparent');
    ctx.fillStyle = deckAura;
    ctx.beginPath();
    ctx.arc(0, 10, 55, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  /* ── 2. Satellite Craft Rendering ── */
  ctx.save();
  ctx.translate(satX, satY);

  const satScale = isMobile ? 1.0 : 1.38;
  ctx.scale(satScale, satScale);

  const satGlow = ctx.createRadialGradient(0, 0, 4, 0, 0, 60);
  satGlow.addColorStop(0, `rgba(0, 242, 254, ${0.40 * satVisibility})`);
  satGlow.addColorStop(1, 'transparent');
  ctx.fillStyle = satGlow;
  ctx.beginPath();
  ctx.arc(0, 0, 60, 0, Math.PI * 2);
  ctx.fill();

  const drawSolarPanel = (x) => {
    ctx.fillStyle = '#0a2e5c';
    ctx.strokeStyle = '#00f2fe';
    ctx.lineWidth = 1;
    ctx.fillRect(x, -9, 32, 18);
    ctx.strokeRect(x, -9, 32, 18);

    ctx.strokeStyle = 'rgba(0, 242, 254, 0.4)';
    for (let cx = x + 8; cx < x + 32; cx += 8) {
      ctx.beginPath();
      ctx.moveTo(cx, -9);
      ctx.lineTo(cx, 9);
      ctx.stroke();
    }
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x + 32, 0);
    ctx.stroke();
  };

  drawSolarPanel(-40);
  drawSolarPanel(8);

  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(-40, 0);
  ctx.lineTo(40, 0);
  ctx.stroke();

  ctx.fillStyle = '#d97706';
  ctx.fillRect(-8, -11, 16, 22);
  ctx.strokeStyle = '#fef08a';
  ctx.lineWidth = 1.2;
  ctx.strokeRect(-8, -11, 16, 22);

  ctx.beginPath();
  ctx.ellipse(0, 13, 12, 5, 0, 0, Math.PI * 2);
  ctx.fillStyle = '#cbd5e1';
  ctx.fill();
  ctx.strokeStyle = '#00f2fe';
  ctx.lineWidth = 1.4;
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(0, 13);
  ctx.lineTo(-6, 20);
  ctx.strokeStyle = '#ef4444';
  ctx.lineWidth = 1.6;
  ctx.stroke();

  const ledBlink = Math.sin(time * 5) > 0 ? 1 : 0.2;
  ctx.beginPath();
  ctx.arc(0, -6, 2.5, 0, Math.PI * 2);
  ctx.fillStyle = `rgba(0, 242, 254, ${ledBlink})`;
  ctx.shadowColor = '#00f2fe';
  ctx.shadowBlur = 8;
  ctx.fill();

  ctx.restore();

  /* ── 3. Holographic HUD Badge ── */
  const hudAlpha = scrollMap(scroll, [
    [0.26, 0.0],
    [0.34, 0.95],
    [0.56, 0.95],
    [0.62, 0.0],
  ]);

  if (hudAlpha > 0.02) {
    const badgeX = targetShip.shipX;
    const badgeY = targetShip.mastY - 42;

    ctx.save();
    ctx.translate(badgeX, badgeY);

    const badgeWidth = isMobile ? 190 : 240;
    const badgeHeight = 30;
    const bx = -badgeWidth / 2;
    const by = -badgeHeight / 2;

    ctx.fillStyle = `rgba(2, 12, 28, ${0.88 * hudAlpha})`;
    ctx.strokeStyle = `rgba(0, 242, 254, ${0.80 * hudAlpha})`;
    ctx.lineWidth = 1.4;
    ctx.shadowColor = '#00f2fe';
    ctx.shadowBlur = 14;

    ctx.beginPath();
    ctx.roundRect(bx, by, badgeWidth, badgeHeight, 8);
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;

    const dotPulse = Math.sin(time * 8) > 0 ? 1 : 0.3;
    ctx.beginPath();
    ctx.arc(bx + 16, 0, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(0, 242, 254, ${dotPulse * hudAlpha})`;
    ctx.fill();

    ctx.font = isMobile ? 'bold 10px monospace' : 'bold 11px monospace';
    ctx.fillStyle = `rgba(0, 242, 254, ${hudAlpha})`;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText('SIGNAL DETECTED', bx + 28, 0);

    ctx.font = '9px monospace';
    ctx.fillStyle = `rgba(148, 163, 184, ${hudAlpha * 0.9})`;
    ctx.textAlign = 'right';
    ctx.fillText('ORCA-SAT // LOCK', bx + badgeWidth - 12, 0);

    ctx.restore();
  }

  ctx.restore();
}
