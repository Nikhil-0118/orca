import React, { ReactNode } from 'react';

interface LayoutProps {
  header: ReactNode;
  chatPanel: ReactNode;
  mapPanel: ReactNode;
  alertPanel: ReactNode;
  sosModal?: ReactNode;
  orcaCompanion?: ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({
  header,
  chatPanel,
  mapPanel,
  alertPanel,
  sosModal,
  orcaCompanion,
}) => {
  return (
    <div className="h-screen w-screen flex flex-col bg-navy-950 text-slate-100 overflow-hidden select-none relative">
      {header}

      {/* Main Grid: Responsive Map + Chat Panel + Alert Sidebar */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-2 p-2 overflow-hidden relative">
        {/* Left Column: Live Marine Map (6 cols) */}
        <section className="lg:col-span-6 h-full rounded-2xl overflow-hidden border border-slate-800/80 relative flex flex-col">
          {mapPanel}
        </section>

        {/* Center Column: Multi-Agent Conversational Hub (4 cols) */}
        <section className="lg:col-span-4 h-full rounded-2xl overflow-hidden border border-slate-800/80 bg-navy-900/60 flex flex-col">
          {chatPanel}
        </section>

        {/* Right Column: Live Re-Alerts & Telemetry Feed (2 cols) */}
        <section className="lg:col-span-2 h-full rounded-2xl overflow-hidden border border-slate-800/80 bg-navy-900/60 flex flex-col relative">
          {alertPanel}
        </section>
      </main>

      {/* ── Dashboard Floating ORCA Companion (Bottom-Right corner: ~24px from bottom & right) ── */}
      {orcaCompanion && (
        <div className="fixed bottom-6 right-6 z-40 pointer-events-auto filter drop-shadow-2xl">
          {orcaCompanion}
        </div>
      )}

      {sosModal}
    </div>
  );
};

