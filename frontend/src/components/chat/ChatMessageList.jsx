import React, { useRef, useEffect } from 'react';
import {
  Anchor,
  Clock,
  Compass,
  Navigation,
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
  HelpCircle,
  Waves,
  Lightbulb,
} from 'lucide-react';
import { AgentActivityPanel } from './AgentActivityPanel';
import { useLanguage } from '../../i18n/LanguageContext';

/**
 * Filters out internal provenance tags like [LIVE OCEAN DATA], [SIMULATED WEATHER DATA], etc.
 * These are backend annotations not meant for end-user display.
 */
function stripProvenanceTags(text) {
  if (typeof text !== 'string') return '';
  return text
    .replace(/\n*\[(?:LIVE|SIMULATED|DEMO|RAG)[^\]]*\][^\n]*/g, '')
    .replace(/\n*Signal Conflict Analysis:[^\n]*/g, '')
    .trim();
}

/**
 * Safely parses bold markdown and bullet lines into clean React elements
 * without dangerouslySetInnerHTML. Never parses or renders raw HTML/SVG markup as text.
 */
function renderFormattedContent(text) {
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
              <strong key={pIdx} style={{ color: 'var(--chat-text-heading, inherit)', fontWeight: 600 }}>
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

export const ChatMessageList = ({
  messages = [],
  isLoading = false,
  locationContext = {},
  onRequestGps,
}) => {
  const { t } = useLanguage();
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="chat-messages-area">
      <div className="chat-messages-inner">
        {messages.map((msg, index) => {
          const isAssistant = msg.role === 'assistant';
          const mode = msg.mode || 'marine';
          const isConversationalOrUtility =
            mode === 'conversational' ||
            mode === 'general' ||
            mode === 'help' ||
            mode === 'greeting';
          const isElevatedRisk = msg.risk_level === 'high' || msg.risk_level === 'critical';
          const hasAgentData =
            (msg.agents_used && msg.agents_used.length > 0) ||
            (msg.evidence && msg.evidence.length > 0) ||
            (msg.structured_evidence && msg.structured_evidence.length > 0);

          return (
            <div key={msg.id || index} className={`chat-msg-row ${isAssistant ? 'assistant' : 'user'}`}>
              {isAssistant && (
                <div className="chat-msg-avatar orca" aria-hidden="true">
                  <img src="/orca-emblem.png" alt="ORCA" style={{ width: 18, height: 18, objectFit: 'contain' }} />
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
                        {t('highRiskAlert', '⚠️ High Maritime Risk: A safety restriction or active hazard is present in this sector.')}
                      </div>
                    )}
                  </>
                )}


                {/* ── Domain-Specific Decision-First Visual Hierarchy ── */}
                {!isConversationalOrUtility && (
                  <>
                    {/* 2. Structured Decision Badge (Hero Element) */}
                    {msg.decision && msg.decision.label && (
                      <div
                        className={`chat-decision-card ${
                          msg.decision.label.toLowerCase().includes('caution')
                            ? 'caution'
                            : msg.decision.label.toLowerCase().includes('not') ||
                              msg.decision.label.toLowerCase().includes('avoid')
                            ? 'danger'
                            : msg.decision.label.toLowerCase().includes('recommend') ||
                              msg.decision.label.toLowerCase().includes('clear')
                            ? 'recommended'
                            : 'neutral'
                        }`}
                      >
                        <div className="chat-decision-header">
                          <div className="chat-decision-title">
                            {msg.decision.label.toLowerCase().includes('caution') ? (
                              <AlertTriangle className="w-4 h-4" aria-hidden="true" />
                            ) : msg.decision.label.toLowerCase().includes('not') ||
                              msg.decision.label.toLowerCase().includes('avoid') ? (
                              <ShieldAlert className="w-4 h-4" aria-hidden="true" />
                            ) : msg.decision.label.toLowerCase().includes('recommend') ||
                              msg.decision.label.toLowerCase().includes('clear') ? (
                              <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                            ) : (
                              <HelpCircle className="w-4 h-4" aria-hidden="true" />
                            )}
                            <span>{t('decisionText', 'Decision')}: {msg.decision.label}</span>
                          </div>
                          {msg.decision.confidence && (
                            <span className="chat-confidence-badge">
                              {t('confidenceText', 'Confidence')}: {msg.decision.confidence}
                            </span>
                          )}
                        </div>
                        {msg.decision.summary && (
                          <div className="chat-decision-summary">{msg.decision.summary}</div>
                        )}
                      </div>
                    )}

                    {/* 3. Key Environmental & Operational Conditions */}
                    {msg.key_conditions && msg.key_conditions.length > 0 && (
                      <div className="chat-conditions-section">
                        <div className="chat-section-label">
                          <Waves className="w-3 h-3 text-cyan-400" aria-hidden="true" />
                          <span>{t('keyConditionsText', 'Key Conditions')}</span>
                        </div>
                        <div className="chat-conditions-grid">
                          {msg.key_conditions.map((cond, cIdx) => (
                            <div key={cIdx} className="chat-condition-pill">
                              <span className="chat-condition-pill-dot" aria-hidden="true" />
                              <span>{cond}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 4. Actionable Recommendations */}
                    {msg.recommendations && msg.recommendations.length > 0 && (
                      <div className="chat-actions" style={{ marginTop: 8 }}>
                        {msg.recommendations.map((action, aIdx) => (
                          <div key={aIdx} className="chat-action-chip">
                            <span className="chat-action-icon" aria-hidden="true">
                              <Compass className="w-3 h-3" style={{ color: '#06b6d4' }} aria-hidden="true" />
                            </span>
                            <span className="chat-action-text">{action}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* 5. Best Timing Window (Transparent / No Fake Precision) */}
                    {msg.best_time && (
                      <div className={`chat-timing-box ${msg.best_time.available ? 'available' : ''}`}>
                        <Clock className="w-3.5 h-3.5 chat-timing-icon text-cyan-400" aria-hidden="true" />
                        <div className="chat-timing-text">
                          {msg.best_time.available && msg.best_time.window ? (
                            <>
                              <strong>{t('bestTimeWindow', 'Best Time Window')}:</strong> {msg.best_time.window}
                              {msg.best_time.basis && <span> · {msg.best_time.basis}</span>}
                            </>
                          ) : (
                            <span>{msg.best_time.basis || t('noTimingForecast', 'No verified future timing forecast available for this period.')}</span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* 6. Why / Reasoning Summary (Concise User Justification) */}
                    {msg.reasoning_summary && (
                      <div className="chat-reasoning-callout">
                        <Lightbulb className="w-3.5 h-3.5 chat-reasoning-icon" aria-hidden="true" />
                        <div>{msg.reasoning_summary}</div>
                      </div>
                    )}

                    {/* 7. Route Info Card */}
                    {msg.route_info && (
                      <div className="chat-route-card" style={{ marginTop: 10 }}>
                        <div className="chat-route-header">
                          <div className="chat-route-name">
                            <Navigation className="w-3.5 h-3.5" aria-hidden="true" />
                            <span>{msg.route_info.destinationName}</span>
                          </div>
                          <span
                            className={`chat-route-badge ${
                              msg.route_info.safetyClearance === 'SAFE'
                                ? 'safe'
                                : msg.route_info.safetyClearance === 'CAUTION'
                                ? 'caution'
                                : 'restricted'
                            }`}
                          >
                            {msg.route_info.safetyClearance}
                          </span>
                        </div>
                        <div className="chat-route-stats">
                          <div>
                            <div className="chat-route-stat-label">{t('distanceKm', 'Distance')}</div>
                            <div className="chat-route-stat-value">{msg.route_info.distanceKm} km</div>
                          </div>
                          <div>
                            <div className="chat-route-stat-label">{t('bearingDeg', 'Bearing')}</div>
                            <div className="chat-route-stat-value" style={{ color: '#06b6d4' }}>
                              {msg.route_info.bearingDegrees}°
                            </div>
                          </div>
                          <div>
                            <div className="chat-route-stat-label">{t('estTimeMin', 'Est. Time')}</div>
                            <div className="chat-route-stat-value">
                              {msg.route_info.estimatedTimeMinutes} min
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* 8. Evidence & Sources + Limitations Panel (Collapsible) */}
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

                {/* Plain or markdown formatted content */}
                {renderFormattedContent(msg.content)}
              </div>
            </div>
          );
        })}

        {/* Loading indicator */}
        {isLoading && (
          <div className="chat-msg-row assistant">
            <div className="chat-msg-avatar orca" aria-hidden="true">
              <img src="/orca-emblem.png" alt="ORCA" style={{ width: 18, height: 18, objectFit: 'contain' }} />
            </div>
            <div className="chat-loading">
              <div className="chat-loading-dots" aria-hidden="true">
                <div className="chat-loading-dot" />
                <div className="chat-loading-dot" />
                <div className="chat-loading-dot" />
              </div>
              <span className="chat-loading-text">{t('planningReasoning', 'ORCA planning and reasoning...')}</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default ChatMessageList;
