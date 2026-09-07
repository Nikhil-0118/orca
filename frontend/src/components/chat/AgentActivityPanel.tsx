import React, { useState } from 'react';
import { ChevronDown, Cpu, FileText, Info, Layers } from 'lucide-react';
import { ReasoningStep, StructuredEvidenceItem } from '../../types/chat.types';

interface AgentActivityPanelProps {
  steps?: ReasoningStep[];
  evidence?: string[];
  structuredEvidence?: StructuredEvidenceItem[];
  dataLimitations?: string[];
  agentsUsed?: string[];
  riskLevel?: string;
}

/**
 * Maps raw agent type identifiers to human-readable display names and colors.
 */
function getAgentBadge(agent: string): { name: string; color: string } {
  const normalized = agent.toLowerCase();
  if (normalized.includes('ocean')) return { name: 'Ocean Agent', color: '#06b6d4' };
  if (normalized.includes('weather')) return { name: 'Weather Agent', color: '#f59e0b' };
  if (normalized.includes('satellite') || normalized.includes('eo')) return { name: 'Satellite EO Agent', color: '#8b5cf6' };
  if (normalized.includes('safety') || normalized.includes('geofence')) return { name: 'Safety Agent', color: '#ef4444' };
  if (normalized.includes('rag') || normalized.includes('knowledge')) return { name: 'Knowledge Base', color: '#10b981' };
  if (normalized.includes('coordinator') || normalized.includes('orchestrator')) return { name: 'Coordinator', color: '#3b82f6' };
  return { name: agent, color: '#64748b' };
}

export const AgentActivityPanel: React.FC<AgentActivityPanelProps> = ({
  steps,
  evidence,
  structuredEvidence,
  dataLimitations,
  agentsUsed,
}) => {
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
      {/* ── Agents Used Tag Bar ── */}
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
            <span className="chat-ui-icon" aria-hidden="true" role="presentation">
              <Layers className="w-3 h-3 text-cyan-400" aria-hidden="true" focusable={false} role="presentation" />
            </span>
            <span>Sources:</span>
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
                  backgroundColor: 'rgba(15, 23, 42, 0.6)',
                  border: `1px solid rgba(100, 116, 139, 0.2)`,
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

      {/* ── Expandable Evidence & Sources Accordion ── */}
      {hasEvidence && (
        <div style={{ marginBottom: hasLimitations ? 6 : 0 }}>
          <button
            type="button"
            className={`chat-agent-toggle ${isEvidenceOpen ? 'expanded' : ''}`}
            onClick={() => setIsEvidenceOpen(!isEvidenceOpen)}
            aria-expanded={isEvidenceOpen}
          >
            <span className="chat-ui-icon" aria-hidden="true" role="presentation">
              {hasSteps ? (
                <Cpu className="w-3.5 h-3.5" aria-hidden="true" focusable={false} role="presentation" />
              ) : (
                <FileText className="w-3.5 h-3.5" aria-hidden="true" focusable={false} role="presentation" />
              )}
            </span>
            <span>Evidence & Sources ({evidenceCount} verified)</span>
            <span className="chat-ui-icon" aria-hidden="true" role="presentation" style={{ marginLeft: 'auto' }}>
              <ChevronDown className="w-3.5 h-3.5 chat-chevron-icon" aria-hidden="true" focusable={false} role="presentation" />
            </span>
          </button>

          {isEvidenceOpen && (
            <div className="chat-agent-details">
              {/* Structured Evidence Items */}
              {hasStructuredEvidence &&
                structuredEvidence.map((item, idx) => {
                  const badge = getAgentBadge(item.source);
                  return (
                    <div key={idx} className="chat-agent-item">
                      <div
                        className="chat-agent-dot"
                        style={{ backgroundColor: badge.color }}
                      />
                      <div style={{ flex: 1 }}>
                        <div
                          className="chat-agent-name"
                          style={{ color: badge.color, fontSize: 11, fontWeight: 700 }}
                        >
                          {badge.name}
                        </div>
                        <div
                          className="chat-agent-rationale"
                          style={{ color: '#cbd5e1', fontSize: 12, marginTop: 2, lineHeight: 1.4 }}
                        >
                          {item.summary}
                        </div>
                      </div>
                    </div>
                  );
                })}

              {/* Step-by-step agent reasoning fallback */}
              {!hasStructuredEvidence &&
                hasSteps &&
                steps.map((step, idx) => {
                  const badge = getAgentBadge(step.agent);
                  return (
                    <div key={idx} className="chat-agent-item">
                      <div
                        className="chat-agent-dot"
                        style={{ backgroundColor: badge.color }}
                      />
                      <div>
                        <div className="chat-agent-name">{badge.name}</div>
                        <div className="chat-agent-rationale">{step.rationale}</div>
                        {step.data_sources_queried.length > 0 && (
                          <div className="chat-agent-sources">
                            Sources: {step.data_sources_queried.join(', ')}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

              {/* Legacy string evidence fallback */}
              {!hasStructuredEvidence &&
                !hasSteps &&
                hasLegacyEvidence &&
                evidence.map((ev, idx) => (
                  <div key={idx} className="chat-agent-item">
                    <div
                      className="chat-agent-dot"
                      style={{
                        backgroundColor: ev.includes('live')
                          ? '#10b981'
                          : ev.includes('mock')
                          ? '#f59e0b'
                          : '#06b6d4',
                      }}
                    />
                    <div>
                      <div
                        className="chat-agent-rationale"
                        style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}
                      >
                        {ev}
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* ── Expandable Data Limitations Accordion ── */}
      {hasLimitations && (
        <div>
          <button
            type="button"
            className={`chat-agent-toggle ${isLimitationsOpen ? 'expanded' : ''}`}
            onClick={() => setIsLimitationsOpen(!isLimitationsOpen)}
            aria-expanded={isLimitationsOpen}
            style={{
              borderColor: 'rgba(245, 158, 11, 0.15)',
              color: '#94a3b8',
            }}
          >
            <span className="chat-ui-icon" aria-hidden="true" role="presentation">
              <Info className="w-3.5 h-3.5 text-amber-400" aria-hidden="true" focusable={false} role="presentation" />
            </span>
            <span>Data Limitations & Notes ({dataLimitations.length})</span>
            <span className="chat-ui-icon" aria-hidden="true" role="presentation" style={{ marginLeft: 'auto' }}>
              <ChevronDown className="w-3.5 h-3.5 chat-chevron-icon" aria-hidden="true" focusable={false} role="presentation" />
            </span>
          </button>

          {isLimitationsOpen && (
            <div
              className="chat-agent-details"
              style={{
                borderColor: 'rgba(245, 158, 11, 0.15)',
                background: 'rgba(15, 23, 42, 0.6)',
              }}
            >
              {dataLimitations.map((lim, idx) => (
                <div key={idx} className="chat-agent-item" style={{ gap: 8 }}>
                  <span style={{ color: '#f59e0b', fontSize: 10, marginTop: 2 }}>•</span>
                  <div style={{ color: '#94a3b8', fontSize: 11.5, lineHeight: 1.45 }}>
                    {lim}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
