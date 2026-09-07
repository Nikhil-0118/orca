import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Sparkles, MessageSquare, Volume2 } from 'lucide-react';
import { OrcaCompanionState } from '../../types/chat.types';

interface OrcaCompanionProps {
  variant?: 'hero' | 'dashboard';
  state?: OrcaCompanionState;
  onClick?: () => void;
  className?: string;
  showLabel?: boolean;
}

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  vx: number;
  vy: number;
  opacity: number;
  life: number;
  maxLife: number;
}

export const OrcaCompanion: React.FC<OrcaCompanionProps> = ({
  variant = 'hero',
  state = 'idle',
  onClick,
  className = '',
  showLabel = true,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [particles, setParticles] = useState<Particle[]>([]);
  
  // Animation state references
  const animRef = useRef({
    time: 0,
    swimCycle: 0,
    diveCycle: 0,
    xOffset: 0,
    yOffset: 0,
    rotation: 0,
    tailFlex: 0,
    finFlex: 0,
    mouseX: 0,
    mouseY: 0,
    targetMouseX: 0,
    targetMouseY: 0,
    nextBubbleTime: 0,
  });

  const nextParticleId = useRef(0);

  // Check prefers-reduced-motion
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Track global mouse position for subtle gaze / parallax
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const dx = (e.clientX - centerX) / window.innerWidth;
    const dy = (e.clientY - centerY) / window.innerHeight;
    animRef.current.targetMouseX = Math.max(-1, Math.min(1, dx * 2));
    animRef.current.targetMouseY = Math.max(-1, Math.min(1, dy * 2));
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [handleMouseMove]);

  // Main 60 FPS animation loop
  const [, setFrameTick] = useState(0);

  useEffect(() => {
    let animationId: number;

    const render = () => {
      const a = animRef.current;
      const speedMultiplier = reducedMotion ? 0.2 : isHovered ? 0.6 : 1.0;
      a.time += 0.02 * speedMultiplier;

      // Smooth mouse interpolation
      a.mouseX += (a.targetMouseX - a.mouseX) * 0.05;
      a.mouseY += (a.targetMouseY - a.mouseY) * 0.05;

      // 1. Organic horizontal swim undulation
      a.swimCycle = (a.swimCycle + 0.025 * speedMultiplier) % (Math.PI * 2);

      // Tail fluke flexing back and forth with swimming rhythm
      a.tailFlex = Math.sin(a.swimCycle * 2.2) * (isHovered ? 6 : 12);
      a.finFlex = Math.sin(a.swimCycle * 1.8 + 0.5) * 4;

      // 2. Periodic diving & cresting cycle (smooth sinusoidal dive wave)
      const divePeriod = variant === 'hero' ? 0.008 : 0.012;
      a.diveCycle += divePeriod * speedMultiplier;
      const diveFactor = Math.sin(a.diveCycle);

      // Vertical offset based on state and dive cycle
      let targetY = Math.sin(a.time * 1.2) * 6 + (diveFactor > 0.3 ? (diveFactor - 0.3) * 28 : 0);
      let targetPitch = Math.sin(a.time * 0.9) * 3 + (diveFactor > 0.3 ? Math.sin(a.diveCycle) * 12 : -Math.sin(a.diveCycle) * 4);

      // State specific adjustments
      if (state === 'listening') {
        targetY = -8 + Math.sin(a.time * 2) * 3;
        targetPitch = -4; // attentive slight upward tilt
      } else if (state === 'thinking') {
        targetY = 16 + Math.sin(a.time * 2.5) * 5; // deeper dive
        targetPitch = 8; // diving angle
      } else if (state === 'answering') {
        targetY = -12 + Math.sin(a.time * 1.5) * 4; // cresting triumphantly upward
        targetPitch = -6;
      }

      // Add gentle mouse parallax tilt
      targetPitch += a.mouseY * 6;
      const targetX = Math.sin(a.time * 0.8) * 8 + a.mouseX * 12;

      a.yOffset += (targetY - a.yOffset) * 0.08;
      a.xOffset += (targetX - a.xOffset) * 0.08;
      a.rotation += (targetPitch - a.rotation) * 0.08;

      // 3. Spawning subtle water bubbles / disturbance particles
      if (a.time > a.nextBubbleTime) {
        const isDivingOrThinking = diveFactor > 0.4 || state === 'thinking' || state === 'listening';
        const rate = isDivingOrThinking ? 0.18 : 0.45;
        a.nextBubbleTime = a.time + rate;

        if (particles.length < 15) {
          const spawnX = -20 + (Math.random() - 0.5) * 10;
          const spawnY = (Math.random() - 0.5) * 8;
          setParticles((prev) => [
            ...prev.slice(-12),
            {
              id: nextParticleId.current++,
              x: spawnX,
              y: spawnY,
              size: Math.random() * 3 + 1.5,
              vx: -(Math.random() * 0.8 + 0.5),
              vy: -(Math.random() * 0.6 + 0.2),
              opacity: 0.7,
              life: 0,
              maxLife: Math.random() * 40 + 30,
            },
          ]);
        }
      }

      // Update particle physics
      setParticles((prev) =>
        prev
          .map((p) => ({
            ...p,
            x: p.x + p.vx,
            y: p.y + p.vy,
            life: p.life + 1,
            opacity: Math.max(0, 0.7 * (1 - p.life / p.maxLife)),
          }))
          .filter((p) => p.life < p.maxLife)
      );

      setFrameTick((t) => (t + 1) % 10000);

      if (!document.hidden) {
        animationId = requestAnimationFrame(render);
      }
    };

    const handleVisibility = () => {
      if (!document.hidden) {
        animationId = requestAnimationFrame(render);
      }
    };

    document.addEventListener('visibilitychange', handleVisibility);
    animationId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationId);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, [variant, state, isHovered, reducedMotion, particles.length]);

  const a = animRef.current;

  // Scale & geometry according to variant
  const isHero = variant === 'hero';
  const baseScale = isHero ? 1.0 : 0.65;
  const hoverScale = isHovered ? baseScale * 1.08 : baseScale;

  return (
    <div
      ref={containerRef}
      role="button"
      tabIndex={0}
      aria-label="Ask ORCA"
      onClick={onClick}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && onClick) {
          e.preventDefault();
          onClick();
        }
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`group relative inline-flex flex-col items-center justify-center cursor-pointer select-none outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-navy-950 rounded-full transition-all duration-300 ${className}`}
      style={{
        transform: `translate3d(${a.xOffset}px, ${a.yOffset}px, 0)`,
        willChange: 'transform',
      }}
    >
      {/* ── Acoustic / Sonar Listening Pulse Rings (when in 'listening' state) ── */}
      {state === 'listening' && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="absolute w-28 h-28 rounded-full border border-cyan-400/40 animate-ping opacity-60"></div>
          <div className="absolute w-36 h-36 rounded-full border border-cyan-300/30 animate-ping opacity-40 [animation-delay:400ms]"></div>
          <div className="absolute w-44 h-44 rounded-full border border-cyan-200/20 animate-ping opacity-20 [animation-delay:800ms]"></div>
        </div>
      )}

      {/* ── Radiant Aura Glow on Answering / Hover ── */}
      <div
        className={`absolute rounded-full pointer-events-none transition-all duration-500 ${
          state === 'answering'
            ? 'w-32 h-32 bg-cyan-400/20 blur-xl scale-125'
            : state === 'thinking'
            ? 'w-28 h-28 bg-blue-500/20 blur-lg scale-110'
            : isHovered
            ? 'w-28 h-28 bg-cyan-500/15 blur-lg scale-110'
            : 'w-20 h-20 bg-cyan-500/5 blur-md'
        }`}
      />

      {/* ── Procedural Bubble Particles Trail ── */}
      <svg className="absolute inset-0 w-full h-full overflow-visible pointer-events-none">
        {particles.map((p) => (
          <circle
            key={p.id}
            cx={50 + p.x}
            cy={40 + p.y}
            r={p.size}
            fill="url(#orcaBubbleGrad)"
            opacity={p.opacity}
          />
        ))}
        <defs>
          <radialGradient id="orcaBubbleGrad" cx="35%" cy="35%" r="65%">
            <stop offset="0%" stopColor="#e0f7fa" stopOpacity="0.9" />
            <stop offset="60%" stopColor="#00f2fe" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#0284c7" stopOpacity="0.2" />
          </radialGradient>
        </defs>
      </svg>

      {/* ── The Anatomical SVG ORCA Body ── */}
      <div
        className="relative transition-transform duration-150"
        style={{
          transform: `scale(${hoverScale}) rotate(${a.rotation}deg)`,
          transformOrigin: '50% 50%',
        }}
      >
        <svg
          width={isHero ? '180' : '120'}
          height={isHero ? '90' : '60'}
          viewBox="0 0 200 100"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="filter drop-shadow-[0_8px_16px_rgba(0,12,30,0.6)]"
        >
          <defs>
            {/* Glossy Dorsal Skin Gradient */}
            <linearGradient id="orcaBlackSkin" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#1e293b" />
              <stop offset="40%" stopColor="#0f172a" />
              <stop offset="85%" stopColor="#020617" />
              <stop offset="100%" stopColor="#000000" />
            </linearGradient>

            {/* Pearlescent White Belly Gradient */}
            <linearGradient id="orcaWhiteBelly" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="70%" stopColor="#f1f5f9" />
              <stop offset="100%" stopColor="#cbd5e1" />
            </linearGradient>

            {/* Subtle Grey Saddle Patch */}
            <linearGradient id="orcaSaddlePatch" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#475569" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#334155" stopOpacity="0.4" />
            </linearGradient>

            {/* Specular Highlight */}
            <linearGradient id="orcaSpecular" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
              <stop offset="50%" stopColor="#ffffff" stopOpacity="0.7" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* 1. Tail Peduncle & Fluke (Articulating / Swimming flex) */}
          <g transform={`rotate(${a.tailFlex} 60 50)`}>
            {/* Peduncle stem */}
            <path
              d="M 65 46 Q 35 48 20 50 Q 35 54 65 56 Z"
              fill="url(#orcaBlackSkin)"
            />
            {/* Flukes (Horizontal killer whale tail fins) */}
            <path
              d="M 22 50 C 14 36 2 34 0 38 C 4 48 10 50 14 50 C 10 50 4 52 0 62 C 2 66 14 64 22 50 Z"
              fill="url(#orcaBlackSkin)"
            />
            {/* Tail fluke white underside edge */}
            <path
              d="M 18 49 C 12 40 4 38 2 41 C 5 47 10 49 14 49 C 10 50 5 53 2 59 C 4 62 12 60 18 51 Z"
              fill="url(#orcaWhiteBelly)"
              opacity="0.9"
            />
          </g>

          {/* 2. Pectoral Fin (Lower side stabilizer) */}
          <path
            d={`M 115 58 C 112 68 100 80 92 84 C 90 82 96 68 105 58 Z`}
            fill="url(#orcaBlackSkin)"
            transform={`rotate(${a.finFlex} 115 58)`}
          />

          {/* 3. Main Torso (Sleek streamlined aerodynamic body) */}
          <path
            d="M 185 50 C 175 36 145 28 115 30 C 85 32 60 44 55 49 C 60 54 85 68 115 70 C 150 72 178 62 185 50 Z"
            fill="url(#orcaBlackSkin)"
          />

          {/* 4. Saddle Patch (Grey marking behind dorsal fin) */}
          <path
            d="M 105 32 C 95 33 88 38 86 42 C 92 44 98 42 104 38 Z"
            fill="url(#orcaSaddlePatch)"
          />

          {/* 5. Iconic Dorsal Fin (Prominent upright curved fin) */}
          <path
            d="M 120 30 C 114 16 110 4 106 2 C 105 8 100 24 94 33 Z"
            fill="url(#orcaBlackSkin)"
          />

          {/* 6. Iconic White Ventral Markings (Chin, throat, belly & flank patch) */}
          <path
            d="M 183 50 C 175 58 155 68 128 68 C 108 68 95 62 82 56 C 88 54 100 52 118 52 C 145 52 172 48 183 50 Z"
            fill="url(#orcaWhiteBelly)"
          />
          <path
            d="M 80 54 C 70 52 62 48 58 49 C 62 53 72 58 82 58 Z"
            fill="url(#orcaWhiteBelly)"
          />

          {/* 7. Distinctive White Eye Patch (Oval marking above/behind eye) */}
          <ellipse
            cx="162"
            cy="44"
            rx="9"
            ry="4.5"
            transform="rotate(-15 162 44)"
            fill="url(#orcaWhiteBelly)"
          />

          {/* 8. Eye (Subtle dark intelligent pupil with specular light) */}
          <circle cx="172" cy="48" r="1.8" fill="#020617" />
          <circle cx="172.5" cy="47.5" r="0.6" fill="#38bdf8" />

          {/* 9. Sleek Specular Back Highlight (Gives realistic wet marine sheen) */}
          <path
            d="M 178 46 C 160 34 135 29 110 31 C 125 33 150 38 170 47 Z"
            fill="url(#orcaSpecular)"
          />

          {/* 10. Blowhole (Subtle slit on top of head) */}
          <ellipse cx="148" cy="31.5" rx="2.5" ry="0.8" fill="#020617" />
        </svg>
      </div>

      {/* ── State Indicator Badge / "ASK ORCA" Label ── */}
      {showLabel && (
        <div
          className={`mt-2 flex items-center gap-1.5 px-3 py-1 rounded-full border transition-all duration-300 shadow-lg backdrop-blur-md ${
            state === 'listening'
              ? 'bg-cyan-950/90 border-cyan-400 text-cyan-300 shadow-cyan-500/30 scale-105'
              : state === 'thinking'
              ? 'bg-blue-950/90 border-blue-400 text-blue-300 shadow-blue-500/30'
              : state === 'answering'
              ? 'bg-emerald-950/90 border-emerald-400 text-emerald-300 shadow-emerald-500/30'
              : isHovered
              ? 'bg-navy-900/90 border-cyan-400 text-cyan-300 shadow-cyan-500/25 scale-105'
              : 'bg-navy-950/80 border-slate-700/60 text-slate-300 group-hover:border-cyan-500/60'
          }`}
        >
          {state === 'listening' ? (
            <>
              <Volume2 className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span className="text-[11px] font-mono font-bold tracking-wider uppercase">Listening...</span>
            </>
          ) : state === 'thinking' ? (
            <>
              <Sparkles className="w-3.5 h-3.5 text-blue-400 animate-spin" />
              <span className="text-[11px] font-mono font-bold tracking-wider uppercase">Synthesizing...</span>
            </>
          ) : state === 'answering' ? (
            <>
              <MessageSquare className="w-3.5 h-3.5 text-emerald-400 animate-bounce" />
              <span className="text-[11px] font-mono font-bold tracking-wider uppercase">ORCA Ready</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3 h-3 text-cyan-400 group-hover:rotate-12 transition-transform" />
              <span className="text-[11px] font-mono font-bold tracking-wider uppercase">
                {isHero ? 'ASK ORCA' : 'ORCA Assistant'}
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
};
