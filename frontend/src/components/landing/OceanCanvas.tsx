import React, { useEffect, useRef } from 'react';
import { RenderContext, clamp } from './OceanJourney/types';
import { drawAtmosphere } from './OceanJourney/drawAtmosphere';
import { drawWaveLayersRange } from './OceanJourney/drawWaves';
import { drawShip } from './OceanJourney/drawShip';
import { drawStorm } from './OceanJourney/drawStorm';
import { drawSatellite } from './OceanJourney/drawSatellite';
import { drawFloatingParticles } from './OceanJourney/drawFloatingParticles';

interface OceanCanvasProps {
  scrollProgress?: number; // 0 to 1
  interactive?: boolean;
}

export const OceanCanvas: React.FC<OceanCanvasProps> = ({
  scrollProgress = 0,
  interactive = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });
  const scrollRef = useRef({ current: 0, target: scrollProgress });

  // Update target scroll whenever prop changes
  useEffect(() => {
    scrollRef.current.target = clamp(scrollProgress, 0, 1);
  }, [scrollProgress]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const speedMultiplier = prefersReducedMotion ? 0.25 : 1.0;

    // Handle high DPI display
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    const handleResize = () => {
      if (!canvas) return;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!interactive) return;
      mouseRef.current.targetX = (e.clientX / width) - 0.5;
      mouseRef.current.targetY = (e.clientY / height) - 0.5;
    };

    window.addEventListener('resize', handleResize);
    if (interactive) {
      window.addEventListener('mousemove', handleMouseMove);
    }

    let time = 0;

    const render = () => {
      time += 0.014 * speedMultiplier;

      // Smooth mouse interpolation for 3D parallax
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.05;

      // Smooth scroll progress interpolation (silky transitions on fast wheel scrolling)
      scrollRef.current.current += (scrollRef.current.target - scrollRef.current.current) * 0.085;
      const smoothScroll = clamp(scrollRef.current.current, 0, 1);

      const isMobile = width < 768;

      const rc: RenderContext = {
        ctx,
        width,
        height,
        time,
        scroll: smoothScroll,
        isMobile,
        mouseX: mouseRef.current.x,
        mouseY: mouseRef.current.y,
      };

      // Reset transform & clear
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      /* ── 1. Atmosphere, Sky Dome, Stars, Storm Clouds, Lightning & Lighthouse ── */
      drawAtmosphere(rc);

      /* ── 2. Deep Background Wave Swells (Layers 0 & 1) ── */
      drawWaveLayersRange(rc, 0, 1);

      /* ── 3. The Vessel (Sits on Wave Layer 2) ── */
      const targetShip = drawShip(rc);

      /* ── 4. Stratospheric Satellite & Pulsing Telemetry Signal Beam to Vessel ── */
      drawSatellite(rc, targetShip);

      /* ── 5. Foreground Waves (Layers 2, 3, 4) — Provides realistic 3D occlusion over ship ── */
      drawWaveLayersRange(rc, 2, 4);

      /* ── 6. Storm Rain Streaks & Sea Spray ── */
      drawStorm(rc);

      /* ── 7. Bioluminescent Phytoplankton & Marine Data Nodes ── */
      drawFloatingParticles(rc);

      if (!document.hidden) {
        animationFrameId = requestAnimationFrame(render);
      }
    };

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        animationFrameId = requestAnimationFrame(render);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [interactive]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none z-0"
      style={{
        willChange: 'transform',
      }}
    />
  );
};
