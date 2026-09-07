import React, { useRef, useEffect } from 'react';
import {
  Anchor,
  Clock,
  Compass,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  HelpCircle,
  Lightbulb,
  ChevronDown,
  Info,
} from 'lucide-react';
import { ChatMessage } from '../../types/chat.types';
import { AgentActivityPanel } from './AgentActivityPanel';
import { SpatialMapCard } from '../map/SpatialMapCard';

interface ChatMessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

/**
 * Filters out internal provenance tags like [LIVE OCEAN DATA], [SIMULATED WEATHER DATA], etc.
 * These are backend annotations not meant for end-user display.
 */
function stripProvenanceTags(text: string): string {
  if (typeof text !== 'string') return '';
  return text
    .replace(/\bsvg(?=[A-Z])/g, '')
    .replace(/\n*\[(?:LIVE|SIMULATED|DEMO|RAG)[^\]]*\][^\n]*/g, '')
    .replace(/\n*Signal Conflict Analysis:[^\n]*/g, '')
    .trim();
}

/**
 * Safely parses bold markdown and bullet lines into clean React elements
 * without dangerouslySetInnerHTML. Never parses or renders raw HTML/SVG markup as text.
 */
function renderFormattedContent(text: string): React.ReactNode {
  if (!text || typeof text !== 'string') return null;

  // Strip provenance tags before rendering
  const cleaned = stripProvenanceTags(text);
  if (!cleaned) return null;

  const lines = cleaned.split('\n');

  return (
    <div className="chat-formatted-text">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} style={{ height: 6 }} />;
        }

        // Check if line is a bullet item
        const isBullet =
          trimmed.startsWith('•') ||
          trimmed.startsWith('- ') ||
          trimmed.startsWith('* ');
        const cleanLine = isBullet
          ? trimmed.replace(/^[•\-\*]\s*/, '')
          : trimmed;

        // Parse bold tokens (**text**) safely into <strong> elements
        const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
        const renderedParts = parts.map((part, pIdx) => {
          if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
            return (
              <strong key={pIdx} style={{ color: '#f8fafc', fontWeight: 600 }}>
                {part.slice(2, -2)}
              </strong>
            );
          }
          return <React.Fragment key={pIdx}>{part}</React.Fragment>;
        });

        if (isBullet) {
          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 8,
                marginTop: 3,
                marginBottom: 3,
                lineHeight: 1.5,
              }}
            >
              <span
                aria-hidden="true"
                style={{ color: '#06b6d4', fontSize: 13, lineHeight: '20px', flexShrink: 0, userSelect: 'none' }}
              >
                •
              </span>
              <span style={{ flex: 1 }}>{renderedParts}</span>
            </div>
          );
        }

        return (
          <p
            key={idx}
            style={{
              margin: '0 0 6px 0',
              lineHeight: 1.55,
            }}
          >
            {renderedParts}
          </p>
        );
      })}
    </div>
  );
}

export const ChatMessageList: React.FC<ChatMessageListProps> = ({ messages, isLoading }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-messages-area">
      <div className="chat-messages-inner">
        {messages.map((msg, index) => {
          const isAssistant = msg.role === 'assistant';
          const mode = msg.mode || 'marine';
          const isConversationalOrUtility = mode === 'conversation' || mode === 'utility';

          const isElevatedRisk = msg.risk_level === 'high' || msg.risk_level === 'critical';
          const hasAgentData =
            (msg.agents_used && msg.agents_used.length > 0) ||
            (msg.evidence && msg.evidence.length > 0) ||
            (msg.structured_evidence && msg.structured_evidence.length > 0);

          return (
            <div
              key={msg.id || index}
              className={`chat-msg-row ${isAssistant ? 'assistant' : 'user'}`}
            >
              {isAssistant && (
                <div className="chat-msg-avatar orca" aria-hidden="true">
                  <span className="chat-ui-icon" aria-hidden="true" role="presentation">
                    <Anchor className="w-3.5 h-3.5" aria-hidden="true" focusable={false} role="presentation" />
                  </span>
                </div>
              )}

              <div className={`chat-msg-bubble ${isAssistant ? 'assistant' : 'user'}`}>
                {/* ── Conditional Domain UI: Only rendered for Marine & Safety modes ── */}
                {!isConversationalOrUtility && (
                  <>
                    {/* High/Critical risk warning banner */}
                    {isElevatedRisk && (hasAgentData || mode === 'safety') && (
                      <div
                        style={{
                          marginBottom: 10,
                          padding: '8px 12px',
                          borderRadius: 8,
                          background: 'rgba(239, 68, 68, 0.12)',
                          border: '1px solid rgba(239, 68, 68, 0.3)',
                          color: '#fca5a5',
                          fontSize: 12,
                          fontWeight: 600,
                        }}
                      >
                        ⚠️ High Maritime Risk: A safety restriction or active hazard is present in this sector.
                      </div>
                    )}
                  </>
                )}

                {/* ── Human-Centered Response UX (Phase 17) ── */}
                {msg.human_response ? (
                  <div className="chat-human-response">
                    {/* 1. Large Direct Answer Header & Prominent Decision Badge */}
                    <div className="chat-human-header">
                      {msg.human_response.decision_code && (
                        <span className={`chat-human-badge badge-${msg.human_response.decision_code.toLowerCase().replace(/\s+/g, '_')}`}>
                          {(msg.human_response.decision_code === 'YES' || msg.human_response.decision_code === 'GO') && <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />}
                          {msg.human_response.decision_code === 'CAUTION' && <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />}
                          {(msg.human_response.decision_code === 'NO' || msg.human_response.decision_code === 'AVOID') && <ShieldAlert className="w-3.5 h-3.5" aria-hidden="true" />}
                          {(msg.human_response.decision_code === 'UNCERTAIN' || msg.human_response.decision_code === 'INSUFFICIENT_DATA') && <HelpCircle className="w-3.5 h-3.5" aria-hidden="true" />}
                          <span>{msg.human_response.decision_code.replace(/_/g, ' ')}</span>
                        </span>
                      )}
                      <h3 className="chat-human-direct">
                        {msg.human_response.direct_answer.replace(
                          /^(?:GO|YES|CAUTION|AVOID|NO|INSUFFICIENT\s*DATA|UNCERTAIN)\s*[—–-]\s*/i,
                          ''
                        )}
                      </h3>
                    </div>

                    {/* 2. Short Plain-Language Explanation */}
                    {msg.human_response.explanation && (
                      <div className="chat-human-explanation">
                        {renderFormattedContent(msg.human_response.explanation)}
                      </div>
                    )}

                    {/* 3. Current Conditions Grid */}
                    {msg.human_response.conditions && (
                      <div className="chat-human-conditions">
                        <div className="chat-conditions-label">Current conditions:</div>
                        <div className="chat-conditions-grid">
                          {msg.human_response.conditions.wind && (
                            <div className="chat-condition-pill">
                              <span className="chat-cond-key">Wind:</span>
                              <span className="chat-cond-val">{msg.human_response.conditions.wind}</span>
                            </div>
                          )}
                          {msg.human_response.conditions.sea_state && (
                            <div className="chat-condition-pill">
                              <span className="chat-cond-key">Sea:</span>
                              <span className="chat-cond-val">{msg.human_response.conditions.sea_state}</span>
                            </div>
                          )}
                          {msg.human_response.conditions.water_temperature && (
                            <div className="chat-condition-pill">
                              <span className="chat-cond-key">Water temp:</span>
                              <span className="chat-cond-val">{msg.human_response.conditions.water_temperature}</span>
                            </div>
                          )}
                          {msg.human_response.conditions.safety && (
                            <div className="chat-condition-pill">
                              <span className="chat-cond-key">Safety:</span>
                              <span className="chat-cond-val">{msg.human_response.conditions.safety}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* 4. Best Time Window (Transparent, only when supported) */}
                    {msg.human_response.best_time && (
                      <div className="chat-human-timing">
                        <Clock className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" />
                        <div className="chat-timing-content">
                          <strong className="chat-timing-label">Best time: </strong>
                          <span>{msg.human_response.best_time}</span>
                        </div>
                      </div>
                    )}

                    {/* 5. Safety Action Notice */}
                    {msg.human_response.safety_notice && (
                      <div className="chat-human-safety">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
                        <div className="chat-safety-content">
                          <strong className="chat-safety-label">Safety action: </strong>
                          <span>{msg.human_response.safety_notice}</span>
                        </div>
                      </div>
                    )}

                    {/* 6. Plain-Language Data Quality Note */}
                    {msg.human_response.data_quality_note && (
                      <div className="chat-human-data-quality">
                        <Info className="w-3 h-3 text-slate-400" aria-hidden="true" />
                        <span>{msg.human_response.data_quality_note}</span>
                      </div>
                    )}

                    {/* Compact Spatial Map Card (Phase 18) */}
                    {msg.spatial?.enabled && (
                      <SpatialMapCard spatial={msg.spatial} />
                    )}

                    {/* 7. Collapsible Secondary Technical Details (Hidden by Default) */}
                    <details className="chat-technical-details">
                      <summary className="chat-technical-summary">
                        <span>View data & source details</span>
                        <ChevronDown className="w-3.5 h-3.5 chevron-icon" aria-hidden="true" />
                      </summary>
                      <div className="chat-technical-content">
                        {msg.human_response.sources && msg.human_response.sources.length > 0 && (
                          <div className="chat-sources-row">
                            <span className="chat-sources-label">Verified sources:</span>
                            <div className="chat-sources-pills">
                              {msg.human_response.sources.map((src, sIdx) => (
                                <span key={sIdx} className="chat-source-tag">{src}</span>
                              ))}
                            </div>
                          </div>
                        )}
                        {(hasAgentData ||
                          (msg.data_limitations && msg.data_limitations.length > 0) ||
                          (msg.reasoning_steps && msg.reasoning_steps.length > 0)) && (
                          <AgentActivityPanel
                            steps={msg.reasoning_steps}
                            evidence={msg.evidence}
                            structuredEvidence={msg.structured_evidence}
                            dataLimitations={msg.data_limitations}
                            agentsUsed={msg.agents_used}
                            riskLevel={msg.risk_level}
                          />
                        )}
                      </div>
                    </details>
                  </div>
                ) : (
                  <>
                    {/* Fallback / Conversational layout for non-marine or legacy responses */}
                    <div className="chat-msg-content" style={{ fontSize: 13.5 }}>
                      {renderFormattedContent(msg.content)}
                    </div>

                    {/* Compact Spatial Map Card for Conversational / Utility branches (Phase 18) */}
                    {msg.spatial?.enabled && (
                      <SpatialMapCard spatial={msg.spatial} />
                    )}

                    {!isConversationalOrUtility && (
                      <>
                        {/* Recommendations */}
                        {msg.recommendations && msg.recommendations.length > 0 && (
                          <div className="chat-actions" style={{ marginTop: 8 }}>
                            {msg.recommendations.map((action, aIdx) => (
                              <div key={aIdx} className="chat-action-chip">
                                <span className="chat-action-icon chat-ui-icon" aria-hidden="true" role="presentation">
                                  <Compass className="w-3 h-3" style={{ color: '#06b6d4' }} aria-hidden="true" focusable={false} role="presentation" />
                                </span>
                                <span className="chat-action-text">{action}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Best Timing Window */}
                        {msg.best_time && (
                          <div className={`chat-timing-box ${msg.best_time.available ? 'available' : ''}`}>
                            <span className="chat-ui-icon chat-timing-icon" aria-hidden="true" role="presentation">
                              <Clock className="w-3.5 h-3.5 text-cyan-400" aria-hidden="true" focusable={false} role="presentation" />
                            </span>
                            <div className="chat-timing-text">
                              {msg.best_time.available && msg.best_time.window ? (
                                <>
                                  <strong>Best Time Window:</strong> {msg.best_time.window}
                                  {msg.best_time.basis && <span> · {msg.best_time.basis}</span>}
                                </>
                              ) : (
                                <span>{msg.best_time.basis || 'No verified future timing forecast available for this period.'}</span>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Reasoning Summary */}
                        {msg.reasoning_summary && (
                          <div className="chat-reasoning-callout">
                            <span className="chat-ui-icon chat-reasoning-icon" aria-hidden="true" role="presentation">
                              <Lightbulb className="w-3.5 h-3.5" aria-hidden="true" focusable={false} role="presentation" />
                            </span>
                            <div>{msg.reasoning_summary}</div>
                          </div>
                        )}

                        {/* Evidence & Sources Panel */}
                        {(hasAgentData ||
                          (msg.data_limitations && msg.data_limitations.length > 0) ||
                          (msg.reasoning_steps && msg.reasoning_steps.length > 0)) && (
                          <div style={{ marginTop: 10 }}>
                            <AgentActivityPanel
                              steps={msg.reasoning_steps}
                              evidence={msg.evidence}
                              structuredEvidence={msg.structured_evidence}
                              dataLimitations={msg.data_limitations}
                              agentsUsed={msg.agents_used}
                              riskLevel={msg.risk_level}
                            />
                          </div>
                        )}
                      </>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}

        {/* Loading indicator */}
        {isLoading && (
          <div className="chat-msg-row assistant">
            <div className="chat-msg-avatar orca" aria-hidden="true">
              <Anchor className="w-3.5 h-3.5" aria-hidden="true" />
            </div>
            <div className="chat-loading">
              <div className="chat-loading-dots" aria-hidden="true">
                <div className="chat-loading-dot" />
                <div className="chat-loading-dot" />
                <div className="chat-loading-dot" />
              </div>
              <span className="chat-loading-text">ORCA planning and reasoning...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
};
