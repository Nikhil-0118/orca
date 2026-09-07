/**
 * drawStorm — Wind-blown diagonal rain particles and wave crest sea spray.
 */
import { RenderContext, scrollMap } from './types';

interface RainDrop {
  x: number;
  y: number;
  length: number;
  speed: number;
  opacity: number;
}

interface SeaSpray {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
  size: number;
}

// Stable pool of rain particles
const RAIN_COUNT = 150;
const rainDrops: RainDrop[] = [];
for (let i = 0; i < RAIN_COUNT; i++) {
  rainDrops.push({
    x: Math.random(),
    y: Math.random(),
    length: 18 + Math.random() * 26,
    speed: 0.7 + Math.random() * 0.6,
    opacity: 0.2 + Math.random() * 0.5,
  });
}

// Sea spray particle pool
const SPRAY_COUNT = 40;
const seaSpray: SeaSpray[] = [];
for (let i = 0; i < SPRAY_COUNT; i++) {
  seaSpray.push({
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    life: 0,
    maxLife: 1,
    size: 2,
  });
}

export function drawStorm(rc: RenderContext): void {
  const { ctx, width, height, scroll, isMobile } = rc;

  // Rain density envelope across phases (peaks at 0.45 - 0.60)
  const rainIntensity = scrollMap(scroll, [
    [0.00, 0.0],
    [0.22, 0.0],
    [0.35, 0.45],
    [0.50, 1.0],
    [0.62, 0.6],
    [0.74, 0.15],
    [0.85, 0.0],
  ]);

  if (rainIntensity <= 0.01) return;

  const maxDrops = Math.floor((isMobile ? 60 : RAIN_COUNT) * rainIntensity);

  /* 1. Diagonal Slashing Rain */
  ctx.save();
  ctx.strokeStyle = 'rgba(180, 220, 255, 0.35)';
  ctx.lineWidth = 1.2;

  const windAngle = 0.35; // radians (~20 deg diagonal)
  const sinAngle = Math.sin(windAngle);
  const cosAngle = Math.cos(windAngle);

  for (let i = 0; i < maxDrops; i++) {
    const drop = rainDrops[i];

    // Move drop diagonally down-right
    drop.y += drop.speed * (0.018 + rainIntensity * 0.025);
    drop.x += drop.speed * sinAngle * (0.018 + rainIntensity * 0.025);

    // Wrap around viewport
    if (drop.y > 1) {
      drop.y = -0.05;
      drop.x = Math.random();
    }
    if (drop.x > 1.1) {
      drop.x = -0.1;
    }

    const startX = drop.x * width;
    const startY = drop.y * height;
    const endX = startX + drop.length * sinAngle * (0.8 + rainIntensity * 0.5);
    const endY = startY + drop.length * cosAngle * (0.8 + rainIntensity * 0.5);

    ctx.strokeStyle = `rgba(180, 225, 255, ${drop.opacity * rainIntensity * 0.6})`;
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.stroke();
  }

  /* 2. Sea Spray Mist / Vapor */
  if (rainIntensity > 0.4) {
    const sprayAlpha = (rainIntensity - 0.4) * 0.3;
    const sprayGrad = ctx.createLinearGradient(0, height * 0.5, 0, height);
    sprayGrad.addColorStop(0, 'transparent');
    sprayGrad.addColorStop(0.7, `rgba(140, 180, 210, ${sprayAlpha * 0.5})`);
    sprayGrad.addColorStop(1, `rgba(100, 150, 190, ${sprayAlpha})`);

    ctx.fillStyle = sprayGrad;
    ctx.fillRect(0, height * 0.4, width, height * 0.6);
  }

  ctx.restore();
}
