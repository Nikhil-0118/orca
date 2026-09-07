import React, { useState, useEffect } from 'react';
import { OceanCanvas } from './OceanCanvas';
import { LandingNavbar } from './LandingNavbar';
import { HeroSection } from './HeroSection';
import { OceanToDataTransition } from './OceanToDataTransition';
import { LiveDataSection } from './LiveDataSection';
import { MultiAgentSection } from './MultiAgentSection';
import { ReasoningFlowSection } from './ReasoningFlowSection';
import { DangerDetectionMap } from './DangerDetectionMap';
import { FinalCtaSection } from './FinalCtaSection';
import { LandingFooter } from './LandingFooter';

interface LandingPageProps {
  onEnterApp: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onEnterApp }) => {
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
      if (totalHeight > 0) {
        setScrollProgress(window.scrollY / totalHeight);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToNext = () => {
    window.scrollTo({
      top: window.innerHeight * 0.85,
      behavior: 'smooth',
    });
  };

  return (
    <div className="relative min-h-screen w-full bg-transparent text-slate-100 overflow-x-hidden">
      {/* Continuous Living Procedural Ocean Background */}
      <OceanCanvas scrollProgress={scrollProgress} interactive={true} />

      {/* Persistent Navigation Header */}
      <LandingNavbar onEnterApp={onEnterApp} />

      {/* Main Story Flow */}
      <main className="relative z-10 flex flex-col w-full">
        {/* 1. Hero — Living Ocean with Animated ORCA Companion */}
        <HeroSection onExplore={scrollToNext} onEnterApp={onEnterApp} scrollProgress={scrollProgress} />

        {/* 2. Transition — Ocean to Satellite Data */}
        <OceanToDataTransition />

        {/* 3. Live Data Ingestion Layer */}
        <LiveDataSection />

        {/* 4. Multi-Agent Reasoning Core */}
        <MultiAgentSection />

        {/* 5. Natural Language Query Reasoning */}
        <ReasoningFlowSection />

        {/* 6. Live Danger Geofencing & Alternate Route Generation */}
        <DangerDetectionMap />

        {/* 7. Final Calm Ocean & Platform Entry */}
        <FinalCtaSection onEnterApp={onEnterApp} />
      </main>

      {/* Footer */}
      <LandingFooter />
    </div>
  );
};
