/**
 * drawFloatingParticles — Subtle bioluminescent phytoplankton and marine data nodes.
 */
import { RenderContext, scrollMap } from './types';

interface MarineNode {
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  pulseSpeed: number;
  pulsePhase: number;
  baseOpacity: number;
}

const NODE_COUNT = 45;
const nodes: MarineNode[] = [];
for (let i = 0; i < NODE_COUNT; i++) {
  nodes.push({
    x: Math.random(),
    y: 0.45 + Math.random() * 0.55,
    size: 0.8 + Math.random() * 1.6,
    speedX: (Math.random() - 0.2) * 0.0006,
    speedY: (Math.random() - 0.5) * 0.0004,
    pulseSpeed: 0.02 + Math.random() * 0.03,
    pulsePhase: Math.random() * Math.PI * 2,
    baseOpacity: 0.2 + Math.random() * 0.5,
  });
}

export function drawFloatingParticles(rc: RenderContext): void {
  const { ctx, width, height, time, scroll, mouseX, mouseY, isMobile } = rc;
  const count = isMobile ? 20 : NODE_COUNT;

  const particleAlpha = scrollMap(scroll, [
    [0.00, 0.7],
    [0.30, 0.4],
    [0.50, 0.2],
    [0.70, 0.6],
    [1.00, 0.8],
  ]);

  ctx.save();

  for (let i = 0; i < count; i++) {
    const n = nodes[i];
    n.x += n.speedX + Math.sin(time * 0.5 + i) * 0.0002;
    n.y += n.speedY;
    n.pulsePhase += n.pulseSpeed;

    if (n.x < 0) n.x = 1;
    if (n.x > 1) n.x = 0;
    if (n.y < 0.45) n.y = 0.95;
    if (n.y > 1.0) n.y = 0.48;

    const px = n.x * width + mouseX * 12;
    const py = n.y * height + mouseY * 10;
    const alpha = n.baseOpacity * (0.6 + 0.4 * Math.sin(n.pulsePhase)) * particleAlpha;

    ctx.beginPath();
    ctx.arc(px, py, n.size, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(0, 242, 254, ${alpha})`;
    ctx.shadowColor = '#00f2fe';
    ctx.shadowBlur = 6;
    ctx.fill();
  }

  ctx.restore();
}
