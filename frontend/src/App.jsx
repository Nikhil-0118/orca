import React, { useState } from 'react';
import { LandingPage } from './components/landing/LandingPage';
import { ChatWorkspace } from './components/chat/ChatWorkspace';
import { LanguageProvider } from './i18n/LanguageContext';
import { ThemeProvider } from './context/ThemeContext';
import { LanguageSelectorModal } from './components/common/LanguageSelectorModal';

const AppContent = () => {
  const [currentView, setCurrentView] = useState('landing');

  return (
    <>
      <LanguageSelectorModal />
      {currentView === 'landing' ? (
        <LandingPage onEnterApp={() => setCurrentView('dashboard')} />
      ) : (
        <ChatWorkspace onBackToLanding={() => setCurrentView('landing')} />
      )}
    </>
  );
};

export const App = () => {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AppContent />
      </LanguageProvider>
    </ThemeProvider>
  );
};

export default App;
