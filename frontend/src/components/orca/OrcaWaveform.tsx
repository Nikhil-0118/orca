import React, { useEffect, useState } from 'react';

interface OrcaWaveformProps {
  isListening: boolean;
  audioLevel?: number; // 0 to 1
  barCount?: number;
  className?: string;
}

export const OrcaWaveform: React.FC<OrcaWaveformProps> = ({
  isListening,
  audioLevel = 0.5,
  barCount = 18,
  className = '',
}) => {
  const [heights, setHeights] = useState<number[]>(() =>
    Array.from({ length: barCount }, () => 15)
  );

  useEffect(() => {
    if (!isListening) {
      setHeights(Array.from({ length: barCount }, () => 8));
      return;
    }

    let frameId: number;
    let phase = 0;

    const updateWaveform = () => {
      phase += 0.15;
      const newHeights = Array.from({ length: barCount }, (_, i) => {
        const centerDistance = Math.abs(i - barCount / 2) / (barCount / 2);
        const envelope = 1 - centerDistance * 0.4;
        const wave = Math.sin(phase + i * 0.4) * 0.5 + 0.5;
        const noise = Math.random() * 0.3;
        const level = Math.max(0.2, audioLevel);
        const height = (wave * 0.7 + noise * 0.3) * envelope * level * 40 + 6;
        return Math.max(6, Math.min(48, height));
      });

      setHeights(newHeights);
      frameId = requestAnimationFrame(updateWaveform);
    };

    frameId = requestAnimationFrame(updateWaveform);
    return () => cancelAnimationFrame(frameId);
  }, [isListening, audioLevel, barCount]);

  return (
    <div
      className={`flex items-center justify-center gap-1 h-12 px-3 py-1.5 rounded-2xl bg-navy-950/80 border border-cyan-900/60 shadow-inner backdrop-blur-md ${className}`}
      aria-label="Microphone audio waveform"
    >
      {heights.map((h, i) => {
        const isCenter = Math.abs(i - barCount / 2) < 3;
        return (
          <div
            key={i}
            className={`w-1 rounded-full transition-all duration-75 ${
              isCenter
                ? 'bg-gradient-to-t from-cyan-500 to-cyan-300 shadow-[0_0_8px_rgba(0,242,254,0.6)]'
                : 'bg-gradient-to-t from-blue-600 to-cyan-400 opacity-80'
            }`}
            style={{
              height: `${h}px`,
              minHeight: '4px',
            }}
          />
        );
      })}
    </div>
  );
};
