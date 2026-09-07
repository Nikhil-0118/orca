/**
 * drawSatellite — High-orbit ISRO / ORCA satellite (+35% larger) positioned at the
 * FAR-RIGHT EDGE (5–12% from right edge), active during storm & rescue phases (30–75% scroll),
 * connecting a wide-aperture pulsing cyan telemetry signal beam to the vessel on the left,
 * before gracefully fading as skies clear and the vessel reaches the lighthouse.
 */
import { RenderContext, scrollMap, lerp } from './types';

export function drawSatellite(
  rc: RenderContext,
  targetShip: { shipX: number; shipY: number; mastY: number },
): void {
  const { ctx, width, height, time, scroll, mouseX, isMobile } = rc;

  // Satellite visibility envelope:
  // 0–30%: Hidden
  // 30–45%: Smoothly enters from the right edge
  // 45–75%: Fully visible at far-right edge (0.90)
  // 75–85%: Weather recovers, fades into high orbit as vessel turns toward lighthouse
  const satVisibility = scrollMap(scroll, [
    [0.00, 0.0],
    [0.30, 0.0],
    [0.45, 1.0],
    [0.75, 1.0],
    [0.85, 0.3],
    [0.90, 0.0],
  ]);

  if (satVisibility <= 0.01) return;

  // Satellite position in the far-right stratosphere (5–12% from right edge)
  const satXRatio = scrollMap(scroll, [
    [0.00, 0.95],
    [0.30, 0.95],
    [0.45, 0.90],
    [1.00, 0.90],
  ]);

  const maxSatX = isMobile ? width - 50 : width - 75;
  const satX = Math.min(maxSatX, width * satXRatio + mouseX * 15 + Math.sin(time * 0.3) * 6);
  const satY = height * 0.14 + Math.cos(time * 0.25) * 5;

  ctx.save();

  /* ── 1. Pulsing Signal Beam Connecting Far-Right Satellite to Left Ship ── */
  const beamIntensity = scrollMap(scroll, [
    [0.00, 0.0],
    [0.32, 0.0],
    [0.45, 0.9],
    [0.60, 1.0],
    [0.75, 0.8],
    [0.82, 0.0],
  ]);

  if (beamIntensity > 0.02) {
    const startX = satX;
    const startY = satY + 10;
    const endX = targetShip.shipX;
    const endY = targetShip.mastY;

    // Outer Cone Beam Haze across wide diagonal
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

    // Sharp Central Core Laser Line
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.strokeStyle = `rgba(220, 250, 255, ${0.95 * beamIntensity * satVisibility})`;
    ctx.lineWidth = 2.8;
    ctx.shadowColor = '#00f2fe';
    ctx.shadowBlur = 18;
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Animated Traveling Telemetry Signal Pulses down the diagonal beam
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

    // Ship Target Lock Reticle & Ground Impact Beacon on Left Ship
    const lockPulse = 1 + Math.sin(time * 6) * 0.15;
    ctx.save();
    ctx.translate(endX, endY);
    ctx.beginPath();
    ctx.arc(0, 0, 26 * lockPulse, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(0, 242, 254, ${0.85 * beamIntensity * satVisibility})`;
    ctx.lineWidth = 2.0;
    ctx.setLineDash([4, 4]);
    ctx.stroke();

    // Lock Crosshairs
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

    // Glowing impact aura on deck
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

  /* ── 2. Satellite Craft Rendering (+35% Larger Size) ── */
  ctx.save();
  ctx.translate(satX, satY);

  // 1.38x Scale (35-40% larger)
  const satScale = isMobile ? 1.0 : 1.38;
  ctx.scale(satScale, satScale);

  // Satellite Ambient Glow
  const satGlow = ctx.createRadialGradient(0, 0, 4, 0, 0, 60);
  satGlow.addColorStop(0, `rgba(0, 242, 254, ${0.40 * satVisibility})`);
  satGlow.addColorStop(1, 'transparent');
  ctx.fillStyle = satGlow;
  ctx.beginPath();
  ctx.arc(0, 0, 60, 0, Math.PI * 2);
  ctx.fill();

  // Solar Array Wings (Left & Right)
  const drawSolarPanel = (x: number) => {
    ctx.fillStyle = '#0a2e5c';
    ctx.strokeStyle = '#00f2fe';
    ctx.lineWidth = 1;
    ctx.fillRect(x, -9, 32, 18);
    ctx.strokeRect(x, -9, 32, 18);

    // Solar cells grid
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

  // Left Solar Array
  drawSolarPanel(-40);
  // Right Solar Array
  drawSolarPanel(8);

  // Connecting Wing Struts
  ctx.strokeStyle = '#64748b';
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(-40, 0);
  ctx.lineTo(40, 0);
  ctx.stroke();

  // Central Core Chassis (Gold & Carbon-fiber)
  ctx.fillStyle = '#d97706';
  ctx.fillRect(-8, -11, 16, 22);
  ctx.strokeStyle = '#fef08a';
  ctx.lineWidth = 1.2;
  ctx.strokeRect(-8, -11, 16, 22);

  // Parabolic Telemetry Dish facing downward toward ship
  ctx.beginPath();
  ctx.ellipse(0, 13, 12, 5, 0, 0, Math.PI * 2);
  ctx.fillStyle = '#cbd5e1';
  ctx.fill();
  ctx.strokeStyle = '#00f2fe';
  ctx.lineWidth = 1.4;
  ctx.stroke();

  // Telemetry Feed Horn angled toward the left-side ship
  ctx.beginPath();
  ctx.moveTo(0, 13);
  ctx.lineTo(-6, 20);
  ctx.strokeStyle = '#ef4444';
  ctx.lineWidth = 1.6;
  ctx.stroke();

  // Blinking Telemetry Status LED
  const ledBlink = Math.sin(time * 5) > 0 ? 1 : 0.2;
  ctx.beginPath();
  ctx.arc(0, -6, 2.5, 0, Math.PI * 2);
  ctx.fillStyle = `rgba(0, 242, 254, ${ledBlink})`;
  ctx.shadowColor = '#00f2fe';
  ctx.shadowBlur = 8;
  ctx.fill();

  ctx.restore();

  /* ── 3. Holographic "SIGNAL DETECTED" HUD Badge ── */
  const hudAlpha = scrollMap(scroll, [
    [0.35, 0.0],
    [0.45, 0.95],
    [0.75, 0.95],
    [0.82, 0.0],
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

    // Glowing Live Telemetry Pulse Dot
    const dotPulse = Math.sin(time * 8) > 0 ? 1 : 0.3;
    ctx.beginPath();
    ctx.arc(bx + 16, 0, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(0, 242, 254, ${dotPulse * hudAlpha})`;
    ctx.fill();

    // Text Label: SIGNAL DETECTED
    ctx.font = isMobile
      ? 'bold 10px monospace'
      : 'bold 11px monospace';
    ctx.fillStyle = `rgba(0, 242, 254, ${hudAlpha})`;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText('SIGNAL DETECTED', bx + 28, 0);

    // Subtitle coordinates / status
    ctx.font = '9px monospace';
    ctx.fillStyle = `rgba(148, 163, 184, ${hudAlpha * 0.9})`;
    ctx.textAlign = 'right';
    ctx.fillText('ISRO-SAT // LOCK', bx + badgeWidth - 12, 0);

    ctx.restore();
  }

  ctx.restore();
}
