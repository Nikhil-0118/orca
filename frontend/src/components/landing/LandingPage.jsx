import React, { useState, useEffect } from 'react';
import { OceanCanvas } from './OceanCanvas.jsx';
import { LandingNavbar } from './LandingNavbar.jsx';
import { HeroSection } from './HeroSection.jsx';
import { OceanToDataTransition } from './OceanToDataTransition.jsx';
import { LiveDataSection } from './LiveDataSection.jsx';
import { MultiAgentSection } from './MultiAgentSection.jsx';
import { ReasoningFlowSection } from './ReasoningFlowSection.jsx';
import { DangerDetectionMap } from './DangerDetectionMap.jsx';
import { FinalCtaSection } from './FinalCtaSection.jsx';
import { LandingFooter } from './LandingFooter.jsx';

export const LandingPage = ({ onEnterApp }) => {
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    let ticking = false;
    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
          if (totalHeight > 0) {
            setScrollProgress(window.scrollY / totalHeight);
          }
          ticking = false;
        });
        ticking = true;
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
    <div className="relative min-h-screen w-full bg-transparent text-slate-900 dark:text-slate-100 overflow-x-hidden">
      {/* Continuous Living Procedural Ocean Background */}
      <OceanCanvas scrollProgress={scrollProgress} interactive={true} onEnterApp={onEnterApp} />

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

        {/* 8. Global Footer */}
        <LandingFooter />
      </main>
    </div>
  );
};

