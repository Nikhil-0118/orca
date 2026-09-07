import React, { useState } from 'react';
import { LandingPage } from './components/landing/LandingPage';
import { ChatWorkspace } from './components/chat/ChatWorkspace';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'landing' | 'dashboard'>('landing');

  if (currentView === 'landing') {
    return <LandingPage onEnterApp={() => setCurrentView('dashboard')} />;
  }

  return <ChatWorkspace onBackToLanding={() => setCurrentView('landing')} />;
};

export default App;
