import React, { useState } from 'react';
import { ChevronDown, Cpu, FileText, Info, Layers } from 'lucide-react';
import { useLanguage } from '../../i18n/LanguageContext';

function getAgentBadge(agent) {
  if (!agent) return { name: 'Unknown', color: '#64748b' };
  const normalized = agent.toLowerCase().replace(/_/g, ' ');
  if (normalized.includes('weather') || normalized.includes('storm')) return { name: 'Weather & Storm Agent', color: '#f59e0b' };
  if (normalized.includes('ocean') || normalized.includes('temp')) return { name: 'Ocean Temperature Agent', color: '#06b6d4' };
  if (normalized.includes('fishing') || normalized.includes('zone')) return { name: 'Fishing Zone Agent', color: '#10b981' };
  if (normalized.includes('safety') || normalized.includes('boundary')) return { name: 'Safety & Boundary Agent', color: '#ef4444' };
  if (normalized.includes('eo') || normalized.includes('satellite') || normalized.includes('earth')) return { name: 'Earth Observation Agent', color: '#8b5cf6' };
  if (normalized.includes('rag') || normalized.includes('knowledge') || normalized.includes('regulatory')) return { name: 'Maritime Knowledge Agent', color: '#a78bfa' };
  if (normalized.includes('final') || normalized.includes('reasoner') || normalized.includes('synthesis')) return { name: 'Final Reasoning Agent', color: '#e2e8f0' };
  if (normalized.includes('coordinator') || normalized.includes('orchestrator')) return { name: 'Coordinator', color: '#3b82f6' };
  return { name: agent, color: '#64748b' };
}

export const AgentActivityPanel = ({
  steps,
  evidence,
  structuredEvidence,
  dataLimitations,
  agentsUsed,
}) => {
  const { t } = useLanguage();
  const [isEvidenceOpen, setIsEvidenceOpen] = useState(false);
  const [isLimitationsOpen, setIsLimitationsOpen] = useState(false);

  const hasSteps = steps && steps.length > 0;
  const hasStructuredEvidence = structuredEvidence && structuredEvidence.length > 0;
  const hasLegacyEvidence = evidence && evidence.length > 0;
  const hasEvidence = hasStructuredEvidence || hasLegacyEvidence || hasSteps;
  const hasLimitations = dataLimitations && dataLimitations.length > 0;
  const hasAgents = agentsUsed && agentsUsed.length > 0;

  if (!hasEvidence && !hasLimitations && !hasAgents) return null;

  const evidenceCount = hasStructuredEvidence
    ? structuredEvidence.length
    : hasSteps
    ? new Set(steps.map((s) => s.agent)).size
    : (evidence?.length || 0);

  return (
    <div className="chat-agent-panel">
      {hasAgents && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            flexWrap: 'wrap',
            marginBottom: 8,
            fontSize: 11,
            color: '#64748b',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontWeight: 600 }}>
            <Layers className="w-3 h-3 text-cyan-400" />
            <span>{t('sourcesLabel', 'Sources:')}</span>
          </span>
          {agentsUsed.map((agentName, idx) => {
            const badge = getAgentBadge(agentName);
            return (
              <span
                key={idx}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '2px 8px',
                  borderRadius: 6,
                  fontSize: 10,
                  fontWeight: 600,
                  backgroundColor: 'var(--chat-input-box-bg, #0d0d0d)',
                  border: '1px solid var(--chat-input-border, rgba(255, 255, 255, 0.08))',
                  color: '#94a3b8',
                }}
              >
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    backgroundColor: badge.color,
                  }}
                />
                {badge.name}
              </span>
            );
          })}
        </div>
      )}

      {hasEvidence && (
        <div style={{ marginBottom: hasLimitations ? 6 : 0 }}>
          <button
            type="button"
            className={`chat-agent-toggle ${isEvidenceOpen ? 'expanded' : ''}`}
            onClick={() => setIsEvidenceOpen(!isEvidenceOpen)}
            aria-expanded={isEvidenceOpen}
          >
            {hasSteps ? <Cpu className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
            <span>{t('evidenceAndActivity', 'Evidence & Sources')} ({evidenceCount})</span>
            <ChevronDown className="w-3.5 h-3.5 chat-chevron-icon" />
          </button>

          {isEvidenceOpen && (
            <div className="chat-agent-details">
              {hasStructuredEvidence &&
                structuredEvidence.map((item, idx) => {
                  const badge = getAgentBadge(item.source);
                  return (
                    <div key={idx} className="chat-agent-item">
                      <div className="chat-agent-dot" style={{ backgroundColor: badge.color }} />
                      <div style={{ flex: 1 }}>
                        <div className="chat-agent-name" style={{ color: badge.color, fontSize: 11, fontWeight: 700 }}>{badge.name}</div>
                        <div className="chat-agent-rationale" style={{ color: '#cbd5e1', fontSize: 12, marginTop: 2, lineHeight: 1.4 }}>{item.summary}</div>
                      </div>
                    </div>
                  );
                })}

              {!hasStructuredEvidence && hasSteps &&
                steps.map((step, idx) => {
                  const badge = getAgentBadge(step.agent);
                  return (
                    <div key={idx} className="chat-agent-item">
                      <div className="chat-agent-dot" style={{ backgroundColor: badge.color }} />
                      <div>
                        <div className="chat-agent-name">{badge.name}</div>
                        <div className="chat-agent-rationale">{step.rationale}</div>
                        {step.data_sources_queried.length > 0 && (
                          <div className="chat-agent-sources">{t('sourcesLabel', 'Sources:')} {step.data_sources_queried.join(', ')}</div>
                        )}
                      </div>
                    </div>
                  );
                })}

              {!hasStructuredEvidence && !hasSteps && hasLegacyEvidence &&
                evidence.map((ev, idx) => (
                  <div key={idx} className="chat-agent-item">
                    <div
                      className="chat-agent-dot"
                      style={{
                        backgroundColor: ev.includes('live') ? '#10b981' : ev.includes('mock') ? '#f59e0b' : '#06b6d4',
                      }}
                    />
                    <div>
                      <div className="chat-agent-rationale" style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>{ev}</div>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {hasLimitations && (
        <div>
          <button
            type="button"
            className={`chat-agent-toggle ${isLimitationsOpen ? 'expanded' : ''}`}
            onClick={() => setIsLimitationsOpen(!isLimitationsOpen)}
            aria-expanded={isLimitationsOpen}
            style={{ borderColor: 'rgba(245, 158, 11, 0.15)', color: '#94a3b8' }}
          >
            <Info className="w-3.5 h-3.5 text-amber-400" />
            <span>{t('dataLimitationsLabel', 'Data Limitations & Notes')} ({dataLimitations.length})</span>
            <ChevronDown className="w-3.5 h-3.5 chat-chevron-icon" />
          </button>

          {isLimitationsOpen && (
            <div className="chat-agent-details" style={{ borderColor: 'rgba(245, 158, 11, 0.15)', background: 'var(--chat-card-bg, #080808)' }}>
              {dataLimitations.map((lim, idx) => (
                <div key={idx} className="chat-agent-item" style={{ gap: 8 }}>
                  <span style={{ color: '#f59e0b', fontSize: 10, marginTop: 2 }}>•</span>
                  <div style={{ color: '#94a3b8', fontSize: 11.5, lineHeight: 1.45 }}>{lim}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
