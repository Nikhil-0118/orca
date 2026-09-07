import React, { useState } from 'react';
import {
  PanelLeftClose,
  PanelLeft,
  ArrowLeft,
  RefreshCw,
  Shield,
  WifiOff,
} from 'lucide-react';
import { ChatSidebar } from './ChatSidebar';
import { ChatContainer } from './ChatContainer';
import { LocationStatusBadge } from './LocationStatusBadge';
import { useGeolocation } from '../../hooks/useGeolocation';
import { useOfflineSafety } from '../../hooks/useOfflineSafety';
import { OfflineSafetyPanel } from '../safety/OfflineSafetyPanel';

interface ChatWorkspaceProps {
  onBackToLanding: () => void;
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({ onBackToLanding }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const {
    locationContext,
    isLocating,
    requestLiveGps,
    setDemoLocation,
    clearDemoLocation,
  } = useGeolocation();
  const [chatKey, setChatKey] = useState(0);
  const [isSafetyModalOpen, setIsSafetyModalOpen] = useState(false);

  // Initialize offline safety engine & simulator
  const safetyHook = useOfflineSafety(
    locationContext.latitude || 9.45,
    locationContext.longitude || 79.2
  );

  const handleNewChat = () => {
    setChatKey((k) => k + 1);
  };

  const { isOffline, evaluation } = safetyHook;

  return (
    <div className="chat-workspace">
      {/* Sidebar */}
      <ChatSidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={handleNewChat}
        onOpenSafety={() => setIsSafetyModalOpen(true)}
        isOffline={isOffline}
      />

      {/* Main Chat Area */}
      <div className="chat-main">
        {/* Top Bar */}
        <div className="chat-topbar">
          <div className="chat-topbar-left">
            <button
              type="button"
              className="chat-topbar-toggle"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
              title={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
            >
              {sidebarOpen ? (
                <PanelLeftClose className="w-4 h-4" />
              ) : (
                <PanelLeft className="w-4 h-4" />
              )}
            </button>

            <span className="chat-topbar-brand">ORCA</span>

            {/* Live Connectivity & Safety Status Pill */}
            <button
              type="button"
              onClick={() => setIsSafetyModalOpen(true)}
              className="chat-topbar-status"
              style={{
                cursor: 'pointer',
                padding: '4px 10px',
                borderRadius: 8,
                background: isOffline
                  ? 'rgba(239, 68, 68, 0.12)'
                  : 'rgba(16, 185, 129, 0.1)',
                border: `1px solid ${
                  isOffline ? 'rgba(239, 68, 68, 0.35)' : 'rgba(16, 185, 129, 0.25)'
                }`,
                color: isOffline ? '#f87171' : '#10b981',
              }}
              title="Click to open Offline Safety Simulator"
            >
              {isOffline ? (
                <>
                  <WifiOff className="w-3.5 h-3.5" />
                  <span>OFFLINE ({evaluation.distanceToBoundaryKm.toFixed(1)}km · {evaluation.state})</span>
                </>
              ) : (
                <>
                  <span className="chat-status-dot" />
                  <span>Online · Safety Active</span>
                </>
              )}
            </button>

            {/* Canonical Location Status Badge (Live GPS vs Demo Mode vs Unavailable) */}
            <LocationStatusBadge
              locationContext={locationContext}
              isLocating={isLocating}
              onRequestGps={requestLiveGps}
              onSetDemo={setDemoLocation}
              onClearDemo={clearDemoLocation}
            />
          </div>

          <div className="chat-topbar-right">
            {/* Safety Simulator Launch Button */}
            <button
              type="button"
              className="chat-topbar-btn"
              onClick={() => setIsSafetyModalOpen(true)}
              title="Open Vessel Simulator & Geofence Engine"
              style={{
                borderColor: isOffline ? 'rgba(239, 68, 68, 0.4)' : 'rgba(6, 182, 212, 0.3)',
                color: isOffline ? '#f87171' : '#06b6d4',
              }}
            >
              <Shield className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Safety Simulator</span>
            </button>

            <button
              type="button"
              className="chat-topbar-btn"
              onClick={handleNewChat}
              title="New conversation"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">New Chat</span>
            </button>

            <button
              type="button"
              className="chat-topbar-btn"
              onClick={onBackToLanding}
              title="Back to overview"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Overview</span>
            </button>
          </div>
        </div>

        {/* Chat Content (Empty State / Messages / Input) */}
        <ChatContainer
          key={chatKey}
          locationContext={locationContext}
          isOffline={isOffline}
          offlineSafetyEval={evaluation}
        />
      </div>

      {/* Offline Safety & Geofence Simulator Modal */}
      <OfflineSafetyPanel
        isOpen={isSafetyModalOpen}
        onClose={() => setIsSafetyModalOpen(false)}
        safetyHook={safetyHook}
      />
    </div>
  );
};

export default ChatWorkspace;
