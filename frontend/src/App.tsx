import React, { useState } from 'react';
import { Header } from './components/common/Header';
import { Layout } from './components/common/Layout';
import { MarineMap } from './components/map/MarineMap';
import { ChatContainer } from './components/chat/ChatContainer';
import { AlertFeed } from './components/alerts/AlertFeed';
import { SosConfirmationModal } from './components/sos/SosConfirmationModal';
import { LandingPage } from './components/landing/LandingPage';
import { OrcaCompanion } from './components/orca/OrcaCompanion';
import { useGeolocation } from './hooks/useGeolocation';
import { initialMapState } from './store/marineMapStore';
import { DestinationPoint } from './types/map.types';
import { OrcaCompanionState } from './types/chat.types';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'landing' | 'dashboard'>('landing');
  const [isSosModalOpen, setIsSosModalOpen] = useState(false);
  const [selectedDestination, setSelectedDestination] = useState<DestinationPoint | null>(null);
  const [companionState, setCompanionState] = useState<OrcaCompanionState>('idle');
  const { location } = useGeolocation();

  if (currentView === 'landing') {
    return <LandingPage onEnterApp={() => setCurrentView('dashboard')} />;
  }

  return (
    <Layout
      header={
        <Header
          onSosClick={() => setIsSosModalOpen(true)}
          onBackToLanding={() => setCurrentView('landing')}
        />
      }
      mapPanel={
        <MarineMap
          vesselLocation={location}
          selectedDestination={selectedDestination}
          fishingZones={initialMapState.fishingZones}
          dangerZones={initialMapState.dangerZones}
          onDestinationSelect={(dest) => setSelectedDestination(dest)}
        />
      }
      chatPanel={
        <ChatContainer
          currentLat={location?.coordinates.latitude}
          currentLon={location?.coordinates.longitude}
          onDestinationSelect={(dest) => setSelectedDestination(dest)}
          onCompanionStateChange={(state) => setCompanionState(state)}
        />
      }
      alertPanel={<AlertFeed />}
      orcaCompanion={
        <OrcaCompanion
          variant="dashboard"
          state={companionState}
          showLabel={false}
          className="hover:scale-110 active:scale-95 transition-transform"
        />
      }
      sosModal={
        <SosConfirmationModal
          isOpen={isSosModalOpen}
          onClose={() => setIsSosModalOpen(false)}
          lat={location?.coordinates.latitude || 13.0827}
          lon={location?.coordinates.longitude || 80.2707}
        />
      }
    />
  );
};

export default App;

