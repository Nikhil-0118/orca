/**
 * drawOrca.js — Realistic Anatomical Killer Whale (Orcinus orca) Swimming & Breach Simulation.
 *
 * Visual Reference Standards:
 * 1. Exact Anatomy: Streamlined black fusiform body, conical rounded melon snout, tall triangular dorsal fin,
 *    paddle-shaped pectoral flippers, narrow caudal peduncle, wide horizontal flukes with center notch,
 *    pure white ventral/jaw/flank markings, white eye patch, grey saddle patch, and wet specular sheen.
 * 2. Motion Mechanics: Spine-propagated kinematics (Tail -> Peduncle -> Torso -> Head).
 * 3. Breach Cycle: Underwater cruise -> acceleration -> ascent -> surface break -> arched breach apex
 *    -> gravity descent -> water re-entry -> dynamic splash/spray/foam -> recovery glide.
 * 4. Realistic Water Interaction: Integrated directly with ocean wave surface (getWaveY).
 */

import { getWaveY } from './drawWaves.js';
import { scrollMap, lerp, clamp } from './types.js';

// Pre-allocated particle pool for water splash, spray droplets, and bubble clouds
const MAX_SPLASH_PARTICLES = 70;
const splashParticles = [];
for (let i = 0; i < MAX_SPLASH_PARTICLES; i++) {
  splashParticles.push({
    active: false,
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    size: 0,
    alpha: 0,
    life: 0,
    maxLife: 0,
    type: 'droplet', // 'droplet', 'sheet', 'foam', 'bubble'
  });
}

function spawnSplashParticle(x, y, vx, vy, size, maxLife, type = 'droplet') {
  for (let i = 0; i < MAX_SPLASH_PARTICLES; i++) {
    const p = splashParticles[i];
    if (!p.active) {
      p.active = true;
      p.x = x;
      p.y = y;
      p.vx = vx;
      p.vy = vy;
      p.size = size;
      p.alpha = 1.0;
      p.life = 0;
      p.maxLife = maxLife;
      p.type = type;
      break;
    }
  }
}

/**
 * Shared interaction state for hit-testing clicks and touches on the Orca and message bubble.
 */
export let orcaInteractionState = {
  active: false,
  x: 0,
  y: 0,
  hitRadius: 115,
  bubble: {
    x: 0,
    y: 0,
    w: 0,
    h: 0,
    active: false,
  },
  isHovered: false,
};

/**
 * Hit test function to check if a screen coordinate (clientX, clientY) lands on the fish or message text.
 */
export function isOrcaHit(clientX, clientY) {
  if (!orcaInteractionState.active) return false;

  // 1. Distance check to the fish's body (covers head, fins, body, flukes)
  const dx = clientX - orcaInteractionState.x;
  const dy = clientY - orcaInteractionState.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  if (dist <= orcaInteractionState.hitRadius) {
    return true;
  }

  // 2. Bounding box check for the message bubble with generous 18px padding
  const b = orcaInteractionState.bubble;
  if (b.active) {
    const halfW = b.w / 2 + 18;
    const halfH = b.h / 2 + 18;
    if (
      clientX >= b.x - halfW &&
      clientX <= b.x + halfW &&
      clientY >= b.y - halfH &&
      clientY <= b.y + halfH
    ) {
      return true;
    }
  }

  return false;
}

/**
 * Main draw call for the ORCA, called from OceanCanvas inside the wave rendering pipeline.
 */
export function drawBreachingOrca(rc) {
  const { ctx, width, height, scroll, mouseX, mouseY, isMobile } = rc;
  const time = rc.time * 5;

  // Visibility envelope: Active in Hero (scroll 0.00 to 0.22), then dives deep
  const orcaHeroAlpha = scrollMap(scroll, [
    [0.00, 1.0],
    [0.12, 0.95],
    [0.22, 0.35],
    [0.32, 0.0],
    [1.00, 0.0],
  ]);

  if (orcaHeroAlpha <= 0.005) {
    orcaInteractionState.active = false;
    return;
  }

  ctx.save();

  // Scale: Majestic size on desktop (~215px body length), compact on mobile
  const baseScale = isMobile ? 0.74 : 1.16;
  // Position: Strictly on the RIGHT side of the hero, avoiding text/CTA/center
  const anchorX = width * (isMobile ? 0.73 : 0.76) + mouseX * 25;
  // Deep dive offset as scroll begins
  const scrollDiveY = scrollMap(scroll, [
    [0.00, 0],
    [0.10, 40],
    [0.22, 160],
    [1.00, 300],
  ]);

  /* ── 1. Breach & Surface Cycle: Jump in ocean -> splash -> surface with big message ── */
  const CYCLE_DURATION = 13.5;
  const cycleTime = (time * 0.90) % CYCLE_DURATION;

  let state = 'ascent';
  let breachProgress = 0;
  let pitchAngle = 0;
  let verticalOffset = 0;
  let spineFlex = 0;
  let tailOscillation = 0;
  let pectoralFlex = 0;
  let rollAngle = 0;
  let trajectoryDriftX = 0;
  let messageAlpha = 0;
  let messageEmergence = 0;
  let showMist = false;

  // Sample the exact water surface level at anchorX
  const waterSurfaceY = getWaveY(anchorX, rc.time, scroll, 2, width, height, mouseY);

  if (cycleTime < 1.2) {
    // Phase 1: Acceleration & Ascent to Jump
    state = 'ascent';
    const ascFrac = cycleTime / 1.2;
    verticalOffset = lerp(24, -14, ascFrac);
    pitchAngle = lerp(0.06, -0.44, Math.pow(ascFrac, 1.3)); // Pitching head upward
    tailOscillation = Math.sin(time * 6.5) * 0.42;
    pectoralFlex = 0.16;
    spineFlex = -0.12 * ascFrac;
    rollAngle = ascFrac * 0.12;
    trajectoryDriftX = lerp(20, 0, ascFrac);

    if (ascFrac > 0.65 && Math.random() < 0.4) {
      spawnSplashParticle(anchorX + 45, waterSurfaceY, (Math.random() * 2 + 1), -Math.random() * 2, 2.5, 25, 'foam');
    }
  } else if (cycleTime < 2.0) {
    // Phase 2: Surface Break
    state = 'break';
    const breakFrac = (cycleTime - 1.2) / 0.8;
    verticalOffset = lerp(-14, -82, breakFrac);
    pitchAngle = lerp(-0.44, -0.58, breakFrac); // Head bursting through surface
    tailOscillation = Math.sin(time * 5.0) * 0.35;
    spineFlex = lerp(-0.12, -0.35, breakFrac);
    rollAngle = lerp(0.12, 0.25, breakFrac);
    trajectoryDriftX = lerp(0, 18, breakFrac);

    if (Math.random() < 0.6) {
      spawnSplashParticle(
        anchorX + 40 + (Math.random() - 0.5) * 25,
        waterSurfaceY,
        (Math.random() * 3 + 1),
        -Math.random() * 4 - 2,
        3.5,
        35,
        'droplet'
      );
    }
  } else if (cycleTime < 3.5) {
    // Phase 3: JUMP IN OCEAN (Apex Arched Breach Pose!)
    state = 'breach';
    const breachFrac = (cycleTime - 2.0) / 1.5;
    breachProgress = Math.sin(breachFrac * Math.PI); // Parabolic flight trajectory
    const apexHeight = isMobile ? 125 : 180;
    verticalOffset = -82 - breachProgress * apexHeight;

    // Curved breach rotation matching the reference image:
    pitchAngle = lerp(-0.58, 0.48, breachFrac);
    spineFlex = -0.40 * (1 - Math.abs(breachFrac - 0.5) * 0.75);
    rollAngle = 0.32 + Math.sin(breachFrac * Math.PI) * 0.22;
    tailOscillation = Math.sin(time * 2.5) * 0.18;
    pectoralFlex = 0.22;
    trajectoryDriftX = lerp(18, 48, breachFrac);

    if (Math.random() < 0.55) {
      spawnSplashParticle(
        anchorX + trajectoryDriftX + (Math.random() - 0.5) * 60,
        waterSurfaceY + verticalOffset + 30,
        (Math.random() - 0.5) * 2.5,
        Math.random() * 2 + 1,
        2.2,
        30,
        'droplet'
      );
    }
  } else if (cycleTime < 4.5) {
    // Phase 4: Gravity Descent
    state = 'descent';
    const descFrac = (cycleTime - 3.5) / 1.0;
    verticalOffset = lerp(-82, 0, Math.pow(descFrac, 1.5));
    pitchAngle = lerp(0.48, 0.64, descFrac); // Diving head downward
    spineFlex = lerp(-0.35, -0.08, descFrac);
    rollAngle = lerp(0.45, 0.15, descFrac);
    tailOscillation = Math.sin(time * 3.0) * 0.22;
    trajectoryDriftX = lerp(48, 60, descFrac);
  } else if (cycleTime < 5.6) {
    // Phase 5: Water Impact & Re-Entry Splash!
    state = 'impact';
    const impactFrac = (cycleTime - 4.5) / 1.1;
    verticalOffset = lerp(0, 42, impactFrac); // Submerging under water
    pitchAngle = lerp(0.64, 0.12, impactFrac);
    spineFlex = Math.sin(time * 4.0) * 0.10;
    rollAngle = 0;
    tailOscillation = Math.sin(time * 4.0) * 0.30;
    trajectoryDriftX = lerp(60, 35, impactFrac);

    // Massive realistic impact splash sheets and spray burst!
    if (impactFrac < 0.35 && Math.random() < 0.85) {
      for (let s = 0; s < 4; s++) {
        const spreadX = (Math.random() - 0.5) * 14;
        spawnSplashParticle(anchorX + 30, waterSurfaceY, spreadX + 2, -Math.random() * 7 - 3, Math.random() * 4 + 2, 45, 'sheet');
        spawnSplashParticle(anchorX + 10, waterSurfaceY, spreadX * 0.8, -Math.random() * 6 - 2, Math.random() * 3 + 1.5, 40, 'droplet');
        spawnSplashParticle(anchorX + 25 + (Math.random() - 0.5) * 40, waterSurfaceY, (Math.random() - 0.5) * 2, 0.5, 6.0, 50, 'foam');
      }
    }
  } else if (cycleTime < 6.8) {
    // Phase 6: Submerged Recovery, Rising Back to Surface
    state = 'surfacing';
    const surfFrac = (cycleTime - 5.6) / 1.2;
    verticalOffset = lerp(42, 6, Math.pow(surfFrac, 0.8)); // Rising right to the water surface!
    pitchAngle = lerp(0.12, -0.04, surfFrac);
    tailOscillation = Math.sin(time * 3.5) * 0.25;
    spineFlex = Math.sin(time * 3.2) * 0.05;
    rollAngle = 0;
    trajectoryDriftX = lerp(35, 0, surfFrac);
  } else {
    // Phase 7: SURFACING & CRUISING WITH BIG MESSAGE: "Need help? Ask ORCA"
    state = 'surface_message';
    const msgTime = cycleTime - 6.8; // 0.0s to 6.7s
    
    // Cruising gracefully right at the water surface (dorsal fin cutting waves)
    verticalOffset = 5 + Math.sin(msgTime * 2.2) * 4;
    pitchAngle = Math.sin(msgTime * 2.0) * 0.04;
    tailOscillation = Math.sin(time * 2.8) * 0.22;
    spineFlex = Math.sin(time * 2.8) * 0.04;
    rollAngle = 0;
    trajectoryDriftX = Math.sin(msgTime * 0.8) * 10;

    // Blowhole mist puff as it surfaces
    if (msgTime < 1.3) {
      showMist = true;
    }

    // Message bubble comes above fish:
    // Emerges with upward drift and fade from 0.2s to 0.7s, stays till 6.1s, then fades
    if (msgTime > 0.2 && msgTime < 6.7) {
      messageAlpha = scrollMap(msgTime, [
        [0.2, 0.0],
        [0.7, 1.0],
        [6.0, 1.0],
        [6.7, 0.0],
      ]);
      // "Coming above fish" upward rise
      const riseProgress = clamp((msgTime - 0.2) / 0.5, 0, 1);
      messageEmergence = (1 - Math.sin(riseProgress * Math.PI * 0.5)) * 18;
    }
  }

  /* ── 2. Update & Draw Dynamic Splash Particles ── */
  updateAndDrawSplashes(ctx, splashParticles, waterSurfaceY, orcaHeroAlpha);

  /* ── 3. Render the Anatomical Killer Whale ── */
  const orcaCenterX = anchorX + trajectoryDriftX;
  const orcaCenterY = waterSurfaceY + verticalOffset + scrollDiveY;

  // Update interaction state for hit-testing and hover
  orcaInteractionState.active = orcaHeroAlpha > 0.1;
  orcaInteractionState.x = orcaCenterX;
  orcaInteractionState.y = orcaCenterY;
  orcaInteractionState.hitRadius = 120 * baseScale;

  ctx.save();
  ctx.translate(orcaCenterX, orcaCenterY);
  ctx.rotate(pitchAngle);
  ctx.scale(baseScale, baseScale);

  // If hovered, apply dynamic interactive cyan glow
  if (orcaInteractionState.isHovered) {
    ctx.shadowColor = 'rgba(56, 189, 248, 0.65)';
    ctx.shadowBlur = 20;
  }

  // If mostly submerged, apply underwater atmospheric scatter
  const isSubmerged = verticalOffset > 15;
  if (isSubmerged) {
    ctx.globalAlpha = (0.75 + 0.25 * (1 - Math.min(1, (verticalOffset - 15) / 35))) * orcaHeroAlpha;
  } else {
    ctx.globalAlpha = 1.0 * orcaHeroAlpha;
  }

  drawAnatomicalOrcaBody(ctx, spineFlex, tailOscillation, pectoralFlex, rollAngle, isSubmerged, time);

  ctx.restore();

  /* ── 4. Surface White Water Ring & Foam at Water Boundary ── */
  if (state === 'break' || state === 'impact' || (state === 'breach' && verticalOffset > -90)) {
    drawSurfaceRuptureFoam(ctx, orcaCenterX, waterSurfaceY, orcaHeroAlpha, time);
  }

  /* ── 5. Blowhole Water Mist as it comes back to surface ── */
  if (showMist) {
    drawBlowholeMist(ctx, orcaCenterX + (baseScale * 50), waterSurfaceY - 10, orcaHeroAlpha, time);
  }

  /* ── 6. BIG Message Text: "Need help? Ask ORCA" Coming Above Fish ── */
  if (messageAlpha > 0.01) {
    const bubbleY = orcaCenterY - (isMobile ? 80 : 105) - messageEmergence;
    drawBigOrcaMessageBubble(
      ctx,
      orcaCenterX,
      bubbleY,
      messageAlpha * orcaHeroAlpha,
      time,
      isMobile,
      orcaInteractionState.isHovered
    );
  } else {
    orcaInteractionState.bubble.active = false;
  }

  ctx.restore();
}

/**
 * Speech Message Bubble in BIG TEXT: "Need help? Ask ORCA"
 * Rendered with dark glassmorphic styling, glowing cyan border, live emerald beacon dot,
 * bold high-visibility typography, and speech pointer.
 */
function drawBigOrcaMessageBubble(ctx, x, y, alpha, time, isMobile, isHovered) {
  ctx.save();
  ctx.translate(x, y);

  // Gentle floating wave bob
  const bobY = Math.sin(time * 3.0) * 3.5;
  ctx.translate(0, bobY);

  const hoverScale = isHovered ? 1.05 : 1.0;
  ctx.scale(hoverScale, hoverScale);

  const primaryText = 'Need help?  Ask ORCA';
  const subText = 'Tap to chat with Marine AI';

  // BIG TYPOGRAPHY: 20px on desktop, 16px on mobile
  const fontSize = isMobile ? 16 : 20;
  ctx.font = `800 ${fontSize}px "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
  const textMetrics = ctx.measureText(primaryText);
  const textWidth = textMetrics.width;

  const padX = isMobile ? 20 : 26;
  const bubbleW = textWidth + padX * 2 + (isMobile ? 40 : 50);
  const bubbleH = isMobile ? 52 : 60;
  const radius = bubbleH / 2;

  // Record bubble coordinates for hit testing in viewport space
  orcaInteractionState.bubble = {
    x: x,
    y: y + bobY,
    w: bubbleW * hoverScale,
    h: bubbleH * hoverScale,
    active: alpha > 0.15,
  };

  // Outer ambient shadow
  ctx.shadowColor = isHovered ? 'rgba(0, 242, 254, 0.55)' : 'rgba(2, 6, 23, 0.75)';
  ctx.shadowBlur = isHovered ? 24 : 16;
  ctx.shadowOffsetY = 6;

  // Dark glassmorphic navy gradient background
  const bgGrad = ctx.createLinearGradient(0, -bubbleH / 2, 0, bubbleH / 2);
  bgGrad.addColorStop(0, `rgba(15, 23, 42, ${0.94 * alpha})`);
  bgGrad.addColorStop(1, `rgba(2, 6, 23, ${0.98 * alpha})`);
  ctx.fillStyle = bgGrad;

  // Rounded Pill
  ctx.beginPath();
  ctx.roundRect(-bubbleW / 2, -bubbleH / 2, bubbleW, bubbleH, radius);
  ctx.fill();

  // Speech bubble pointer arrow pointing down towards the Orca
  ctx.beginPath();
  ctx.moveTo(-9, bubbleH / 2 - 1);
  ctx.lineTo(0, bubbleH / 2 + 9);
  ctx.lineTo(9, bubbleH / 2 - 1);
  ctx.closePath();
  ctx.fill();

  // Glowing Cyan/Teal border
  ctx.shadowColor = isHovered ? '#38bdf8' : '#00f2fe';
  ctx.shadowBlur = isHovered ? 14 : 8;
  ctx.strokeStyle = isHovered
    ? `rgba(56, 189, 248, ${0.98 * alpha})`
    : `rgba(56, 189, 248, ${0.85 * alpha})`;
  ctx.lineWidth = isHovered ? 2.2 : 1.6;
  ctx.stroke();

  // Pointer border
  ctx.beginPath();
  ctx.moveTo(-9, bubbleH / 2);
  ctx.lineTo(0, bubbleH / 2 + 9);
  ctx.lineTo(9, bubbleH / 2);
  ctx.stroke();

  ctx.shadowBlur = 0;

  // Live emerald beacon dot
  const dotX = -bubbleW / 2 + padX + 4;
  const dotY = isMobile ? -6 : -7;

  // Animated outer ring
  const pulseRing = (Math.sin(time * 4) + 1) * 0.5;
  ctx.beginPath();
  ctx.arc(dotX, dotY, 6 + pulseRing * 3, 0, Math.PI * 2);
  ctx.strokeStyle = `rgba(52, 211, 153, ${0.45 * (1 - pulseRing) * alpha})`;
  ctx.lineWidth = 1.4;
  ctx.stroke();

  // Inner live dot
  ctx.beginPath();
  ctx.arc(dotX, dotY, 4.5, 0, Math.PI * 2);
  ctx.fillStyle = '#10b981';
  ctx.shadowColor = '#34d399';
  ctx.shadowBlur = 8;
  ctx.fill();
  ctx.shadowBlur = 0;

  // BIG TEXT: "Need help?  Ask ORCA"
  ctx.font = `800 ${fontSize}px "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
  ctx.fillStyle = `rgba(255, 255, 255, ${0.99 * alpha})`;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'middle';
  ctx.shadowColor = 'rgba(0, 0, 0, 0.6)';
  ctx.shadowBlur = 4;
  ctx.fillText(primaryText, dotX + 15, dotY);
  ctx.shadowBlur = 0;

  // Action hint subtext
  const subFontSize = isMobile ? 10 : 11;
  ctx.font = `600 ${subFontSize}px "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
  ctx.fillStyle = `rgba(56, 189, 248, ${0.92 * alpha})`;
  ctx.fillText(subText, dotX + 15, dotY + (isMobile ? 17 : 19));

  // Chat chevron / arrow on right
  const arrowX = bubbleW / 2 - (isMobile ? 20 : 24);
  ctx.fillStyle = `rgba(255, 255, 255, ${0.85 * alpha})`;
  ctx.font = `bold ${isMobile ? 14 : 16}px sans-serif`;
  ctx.fillText('↗', arrowX, 0);

  ctx.restore();
}

/**
 * Translucent water spray mist emitted from the blowhole when surfacing.
 */
function drawBlowholeMist(ctx, x, y, alpha, time) {
  ctx.save();
  ctx.translate(x, y);

  const mistHeight = 36 + Math.sin(time * 8) * 6;
  const mistGrad = ctx.createLinearGradient(0, 0, 8, -mistHeight);
  mistGrad.addColorStop(0, `rgba(255, 255, 255, ${0.65 * alpha})`);
  mistGrad.addColorStop(0.5, `rgba(186, 230, 253, ${0.35 * alpha})`);
  mistGrad.addColorStop(1, 'transparent');

  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.quadraticCurveTo(8, -mistHeight * 0.5, 14, -mistHeight);
  ctx.lineTo(-8, -mistHeight);
  ctx.quadraticCurveTo(-4, -mistHeight * 0.5, 0, 0);
  ctx.closePath();
  ctx.fillStyle = mistGrad;
  ctx.fill();

  ctx.restore();
}

/**
 * Anatomically precise Orcinus orca Vector Renderer (Strictly matching reference photography).
 */
function drawAnatomicalOrcaBody(ctx, spineFlex, tailAngle, finFlex, roll, isSubmerged, time) {
  ctx.save();

  // Wet skin specular lighting angle
  const wetSheen = Math.sin(time * 2.0) * 0.15 + 0.85;

  /* ── 1. Tail Peduncle & Flukes (Articulating Horizontal Marine Flukes) ── */
  ctx.save();
  // Rotate peduncle from rear spine pivot
  ctx.translate(-70, 0);
  ctx.rotate(tailAngle + spineFlex * 0.8);

  // Narrow Caudal Peduncle Stem with upper/lower muscular keels
  ctx.beginPath();
  ctx.moveTo(0, -9);
  ctx.quadraticCurveTo(-32, -6 + spineFlex * 10, -56, -3);
  ctx.lineTo(-56, 3);
  ctx.quadraticCurveTo(-32, 6 + spineFlex * 10, 0, 9);
  ctx.closePath();

  const peduncleGrad = ctx.createLinearGradient(-56, -9, 0, 9);
  peduncleGrad.addColorStop(0, '#020617');
  peduncleGrad.addColorStop(0.5, '#0f172a');
  peduncleGrad.addColorStop(1, '#020617');
  ctx.fillStyle = peduncleGrad;
  ctx.fill();

  // Broad Horizontal Tail Flukes with Center Notch (Iconic Killer Whale Flukes)
  ctx.save();
  ctx.translate(-56, 0);
  ctx.beginPath();
  // Left fluke blade
  ctx.moveTo(0, 0);
  ctx.bezierCurveTo(-8, -18, -18, -32, -26, -34);
  ctx.bezierCurveTo(-24, -22, -18, -8, -4, -1);
  // Median notch
  ctx.lineTo(-6, 0);
  // Right fluke blade
  ctx.lineTo(-4, 1);
  ctx.bezierCurveTo(-18, 8, -24, 22, -26, 34);
  ctx.bezierCurveTo(-18, 32, -8, 18, 0, 0);
  ctx.closePath();

  const flukeGrad = ctx.createLinearGradient(-26, -34, 0, 34);
  flukeGrad.addColorStop(0, '#020617');
  flukeGrad.addColorStop(0.5, '#1e293b');
  flukeGrad.addColorStop(1, '#020617');
  ctx.fillStyle = flukeGrad;
  ctx.fill();

  // White underside edging on tail flukes
  ctx.strokeStyle = 'rgba(241, 245, 249, 0.75)';
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(-24, -30);
  ctx.quadraticCurveTo(-14, -12, -4, -1);
  ctx.moveTo(-24, 30);
  ctx.quadraticCurveTo(-14, 12, -4, 1);
  ctx.stroke();

  ctx.restore();
  ctx.restore();

  /* ── 2. Far Pectoral Flipper (Projected behind body) ── */
  ctx.save();
  ctx.translate(22, 14);
  ctx.rotate(0.35 + finFlex);
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.bezierCurveTo(8, 22, 4, 38, -10, 44);
  ctx.bezierCurveTo(-16, 38, -14, 20, 0, 0);
  ctx.closePath();
  ctx.fillStyle = '#020617';
  ctx.fill();
  ctx.restore();

  /* ── 3. Main Streamlined Fusiform Torso & Conical Melon Head ── */
  // Curved spine deformation points
  const headX = 94;
  const headY = 2 + spineFlex * 18;
  const snoutX = 108;
  const snoutY = 7 + spineFlex * 22;
  const chinX = 98;
  const chinY = 16 + spineFlex * 20;

  ctx.beginPath();
  // Snout tip (rounded conical melon)
  ctx.moveTo(snoutX, snoutY);
  // Forehead & melon crown curving back
  ctx.bezierCurveTo(98, -4 + spineFlex * 12, 70, -18 + spineFlex * 8, 32, -22 + spineFlex * 2);
  // Back ridge leading to dorsal fin base
  ctx.bezierCurveTo(2, -24, -28, -20, -70, -9);
  // Lower peduncle transition
  ctx.lineTo(-70, 9);
  // Ventral belly curve
  ctx.bezierCurveTo(-35, 19, 5, 26, 42, 24);
  // Throat groove up to chin
  ctx.bezierCurveTo(72, 22, chinX, chinY, snoutX, snoutY);
  ctx.closePath();

  // Jet-Black Skin with gloss gradient
  const skinGrad = ctx.createLinearGradient(30, -25, 30, 25);
  skinGrad.addColorStop(0, '#1e293b');
  skinGrad.addColorStop(0.3, '#0f172a');
  skinGrad.addColorStop(0.75, '#020617');
  skinGrad.addColorStop(1, '#000000');
  ctx.fillStyle = skinGrad;
  ctx.fill();

  /* ── 4. Iconic Saddle Patch (Grey marking directly behind dorsal fin) ── */
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(-4, -22 + spineFlex * 3);
  ctx.bezierCurveTo(-16, -20, -26, -14, -32, -10);
  ctx.bezierCurveTo(-24, -8, -12, -12, -4, -18);
  ctx.closePath();
  ctx.fillStyle = 'rgba(100, 116, 139, 0.75)'; // Slate-grey saddle
  ctx.fill();
  ctx.restore();

  /* ── 5. Iconic Tall Triangular Dorsal Fin ── */
  ctx.save();
  ctx.translate(6, -22 + spineFlex * 3);
  ctx.rotate(-0.08 + spineFlex * 0.4);
  ctx.beginPath();
  ctx.moveTo(-16, 0);
  // Leading edge curves up high
  ctx.bezierCurveTo(-8, -25, -2, -54, 4, -62);
  // Rounded tip & concave swept-back trailing edge
  ctx.bezierCurveTo(3, -56, 4, -34, 14, 0);
  ctx.closePath();

  const dorsalGrad = ctx.createLinearGradient(-10, -60, 10, 0);
  dorsalGrad.addColorStop(0, '#020617');
  dorsalGrad.addColorStop(0.6, '#0f172a');
  dorsalGrad.addColorStop(1, '#020617');
  ctx.fillStyle = dorsalGrad;
  ctx.fill();
  ctx.restore();

  /* ── 6. Iconic White Ventral Markings (Lower jaw, chest, belly, and flank patch) ── */
  ctx.save();
  ctx.beginPath();
  // Lower jaw & throat white
  ctx.moveTo(snoutX - 2, snoutY + 3);
  ctx.bezierCurveTo(88, 16, 68, 22, 40, 22);
  // Belly white contour
  ctx.bezierCurveTo(10, 22, -15, 18, -35, 14);
  // Classic upward-angled flank trident lobe
  ctx.bezierCurveTo(-45, 8, -52, 2, -62, 5);
  ctx.bezierCurveTo(-52, 12, -42, 16, -30, 18);
  // Bottom return to jaw
  ctx.bezierCurveTo(15, 25, 60, 24, chinX, chinY);
  ctx.closePath();

  const whiteGrad = ctx.createLinearGradient(0, 5, 0, 25);
  whiteGrad.addColorStop(0, '#ffffff');
  whiteGrad.addColorStop(0.65, '#f8fafc');
  whiteGrad.addColorStop(1, '#cbd5e1');
  ctx.fillStyle = whiteGrad;
  ctx.fill();
  ctx.restore();

  /* ── 7. Distinctive White Eye Patch (Oval marking above/behind eye) ── */
  ctx.save();
  ctx.translate(72, 3 + spineFlex * 15);
  ctx.rotate(-0.24); // Angled upward and backward
  ctx.beginPath();
  ctx.ellipse(0, 0, 10, 4.5, 0, 0, Math.PI * 2);
  ctx.fillStyle = '#ffffff';
  ctx.shadowColor = 'rgba(255, 255, 255, 0.4)';
  ctx.shadowBlur = 4;
  ctx.fill();
  ctx.shadowBlur = 0;
  ctx.restore();

  /* ── 8. Intelligent Marine Mammal Eye ── */
  ctx.beginPath();
  ctx.arc(81, 7 + spineFlex * 17, 1.8, 0, Math.PI * 2);
  ctx.fillStyle = '#020617';
  ctx.fill();
  // Specular gleam in eye
  ctx.beginPath();
  ctx.arc(81.5, 6.5 + spineFlex * 17, 0.6, 0, Math.PI * 2);
  ctx.fillStyle = '#38bdf8';
  ctx.fill();

  /* ── 9. Near Pectoral Flipper (Foreground spatulate paddle) ── */
  ctx.save();
  ctx.translate(34, 16);
  ctx.rotate(0.28 + finFlex * 1.5);
  ctx.beginPath();
  ctx.moveTo(0, 0);
  // Curved paddle shape
  ctx.bezierCurveTo(12, 18, 14, 38, -2, 48);
  ctx.bezierCurveTo(-14, 42, -16, 22, 0, 0);
  ctx.closePath();

  const flipperGrad = ctx.createLinearGradient(0, 0, 5, 45);
  flipperGrad.addColorStop(0, '#0f172a');
  flipperGrad.addColorStop(0.7, '#020617');
  flipperGrad.addColorStop(1, '#000000');
  ctx.fillStyle = flipperGrad;
  ctx.fill();

  // White underside tip highlight on flipper
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
  ctx.lineWidth = 1;
  ctx.stroke();
  ctx.restore();

  /* ── 10. Wet Gloss Specular Highlights (Natural glistening marine sheen) ── */
  if (!isSubmerged) {
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(88, -2 + spineFlex * 14);
    ctx.bezierCurveTo(65, -14, 35, -20, 5, -21);
    ctx.strokeStyle = `rgba(255, 255, 255, ${0.45 * wetSheen})`;
    ctx.lineWidth = 2.0;
    ctx.stroke();

    // Melon forehead highlight
    ctx.beginPath();
    ctx.ellipse(96, 3 + spineFlex * 18, 8, 3, -0.2, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255, 255, 255, ${0.28 * wetSheen})`;
    ctx.fill();
    ctx.restore();
  }

  // Blowhole slit
  ctx.beginPath();
  ctx.ellipse(56, -14 + spineFlex * 6, 2.8, 0.9, -0.1, 0, Math.PI * 2);
  ctx.fillStyle = '#020617';
  ctx.fill();

  ctx.restore();
}

/**
 * Updates and renders ballistic water splash sheets, airborne spray droplets, and floating surface foam.
 */
function updateAndDrawSplashes(ctx, particles, waterY, alpha) {
  ctx.save();

  for (let i = 0; i < particles.length; i++) {
    const p = particles[i];
    if (!p.active) continue;

    // Physics step
    p.life++;
    if (p.life >= p.maxLife) {
      p.active = false;
      continue;
    }

    p.x += p.vx;
    p.y += p.vy;

    if (p.type === 'droplet' || p.type === 'sheet') {
      p.vy += 0.22; // Gravity
      p.vx *= 0.97; // Air drag
    } else if (p.type === 'foam') {
      p.vx *= 0.92;
      p.size += 0.15; // Expanding foam patch
    }

    const lifeRatio = p.life / p.maxLife;
    p.alpha = (1 - lifeRatio) * alpha;

    ctx.beginPath();
    ctx.arc(p.x, p.y, Math.max(0.5, p.size), 0, Math.PI * 2);

    if (p.type === 'sheet') {
      ctx.fillStyle = `rgba(240, 249, 255, ${0.75 * p.alpha})`;
    } else if (p.type === 'droplet') {
      ctx.fillStyle = `rgba(224, 242, 254, ${0.85 * p.alpha})`;
    } else {
      ctx.fillStyle = `rgba(255, 255, 255, ${0.45 * p.alpha})`;
    }

    ctx.fill();
  }

  ctx.restore();
}

/**
 * Surface rupture foam rings when breaking the water boundary.
 */
function drawSurfaceRuptureFoam(ctx, x, y, alpha, time) {
  ctx.save();
  const foamW = 65 + Math.sin(time * 3) * 10;
  const foamH = 9 + Math.sin(time * 2) * 3;

  ctx.beginPath();
  ctx.ellipse(x, y, foamW, foamH, 0, 0, Math.PI * 2);
  ctx.fillStyle = `rgba(255, 255, 255, ${0.45 * alpha})`;
  ctx.shadowColor = '#bae6fd';
  ctx.shadowBlur = 8;
  ctx.fill();
  ctx.shadowBlur = 0;

  // Secondary outer froth ring
  ctx.beginPath();
  ctx.ellipse(x, y + 2, foamW * 1.35, foamH * 1.4, 0, 0, Math.PI * 2);
  ctx.strokeStyle = `rgba(224, 242, 254, ${0.35 * alpha})`;
  ctx.lineWidth = 1.6;
  ctx.stroke();

  ctx.restore();
}
