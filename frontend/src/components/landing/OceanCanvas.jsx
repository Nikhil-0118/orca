import React, { useEffect, useRef } from 'react';
import { clamp } from './OceanJourney/types.js';
import { drawAtmosphere } from './OceanJourney/drawAtmosphere.js';
import { drawWaveLayersRange } from './OceanJourney/drawWaves.js';
import { drawShip } from './OceanJourney/drawShip.js';
import { drawStorm } from './OceanJourney/drawStorm.js';
import { drawSatellite } from './OceanJourney/drawSatellite.js';
import { drawFloatingParticles } from './OceanJourney/drawFloatingParticles.js';
import { drawUnderwater } from './OceanJourney/drawUnderwater.js';
import { drawBreachingOrca, isOrcaHit, orcaInteractionState } from './OceanJourney/drawOrca.js';

const OceanCanvasComponent = ({
  scrollProgress = 0,
  interactive = true,
  onEnterApp,
}) => {
  const canvasRef = useRef(null);
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

    let animationFrameId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const speedMultiplier = prefersReducedMotion ? 0.25 : 1.0;

    // Handle high DPI display adaptively for smooth 60 FPS on low-end devices
    const isLowEnd =
      (typeof navigator !== 'undefined' && (
        (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) ||
        (navigator.deviceMemory && navigator.deviceMemory <= 4)
      )) || window.innerWidth < 768;
    const maxDpr = isLowEnd ? 1.25 : 1.75;
    const dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
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

    let lastTriggerTime = 0;
    const triggerChatbot = (e) => {
      const now = Date.now();
      if (now - lastTriggerTime < 800) return;
      lastTriggerTime = now;
      if (onEnterApp) {
        if (e && e.preventDefault) e.preventDefault();
        onEnterApp();
      }
    };

    const handleGlobalClick = (e) => {
      if (isOrcaHit(e.clientX, e.clientY)) {
        triggerChatbot(e);
      }
    };

    const handleGlobalTouch = (e) => {
      if (!e.changedTouches || e.changedTouches.length === 0) return;
      const touch = e.changedTouches[0];
      if (isOrcaHit(touch.clientX, touch.clientY)) {
        triggerChatbot(e);
      }
    };

    let lastHitCheck = 0;
    const handleMouseMove = (e) => {
      if (!interactive) return;
      mouseRef.current.targetX = (e.clientX / width) - 0.5;
      mouseRef.current.targetY = (e.clientY / height) - 0.5;

      const now = performance.now();
      if (now - lastHitCheck > 50) {
        lastHitCheck = now;
        const hit = isOrcaHit(e.clientX, e.clientY);
        orcaInteractionState.isHovered = hit;
        if (hit) {
          document.body.style.cursor = 'pointer';
        } else if (document.body.style.cursor === 'pointer') {
          document.body.style.cursor = '';
        }
      }
    };

    window.addEventListener('resize', handleResize, { passive: true });
    window.addEventListener('click', handleGlobalClick, { capture: true });
    window.addEventListener('touchend', handleGlobalTouch, { capture: true, passive: false });
    if (interactive) {
      window.addEventListener('mousemove', handleMouseMove, { passive: true });
    }

    let time = 0;
    const rc = {
      ctx,
      width: 0,
      height: 0,
      time: 0,
      scroll: 0,
      isMobile: false,
      mouseX: 0,
      mouseY: 0,
    };

    const render = () => {
      time += 0.014 * speedMultiplier;

      // Smooth mouse interpolation for 3D parallax
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.05;

      // Smooth scroll progress interpolation
      scrollRef.current.current += (scrollRef.current.target - scrollRef.current.current) * 0.085;
      const smoothScroll = clamp(scrollRef.current.current, 0, 1);

      const isMobile = width < 768;

      rc.width = width;
      rc.height = height;
      rc.time = time;
      rc.scroll = smoothScroll;
      rc.isMobile = isMobile;
      rc.mouseX = mouseRef.current.x;
      rc.mouseY = mouseRef.current.y;

      // Reset transform & clear
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      /* ── 1. Atmosphere, Sky Dome, Clouds & Lightning ── */
      drawAtmosphere(rc);

      /* ── 2. Deep Background Wave Swells (Layers 0 & 1) ── */
      drawWaveLayersRange(rc, 0, 1);

      /* ── 3. The Vessel (Sits on Wave Layer 2) ── */
      const targetShip = drawShip(rc);

      /* ── 4. Stratospheric Satellite & Telemetry Beam ── */
      drawSatellite(rc, targetShip);

      /* ── 5. Midground Wave Layer 2 ── */
      drawWaveLayersRange(rc, 2, 2);

      /* ── 6. Majestic Breaching Killer Whale (Orcinus orca) in the Living Ocean ── */
      drawBreachingOrca(rc);

      /* ── 7. Foreground Waves (Layers 3, 4) ── */
      drawWaveLayersRange(rc, 3, 4);

      /* ── 6. Storm Rain Streaks & Sea Spray ── */
      drawStorm(rc);

      /* ── 7. Bioluminescent Phytoplankton & Marine Data Nodes ── */
      drawFloatingParticles(rc);

      /* ── 8. Underwater Research Scene (Expands past 75% scroll with submarines & bio-research) ── */
      drawUnderwater(rc);

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
      window.removeEventListener('click', handleGlobalClick, { capture: true });
      window.removeEventListener('touchend', handleGlobalTouch, { capture: true });
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (document.body.style.cursor === 'pointer') {
        document.body.style.cursor = '';
      }
    };
  }, [interactive, onEnterApp]);

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

export const OceanCanvas = React.memo(OceanCanvasComponent);
