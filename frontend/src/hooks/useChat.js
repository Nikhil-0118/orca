/**
 * useChat hook (Phase 18 — JSX conversion with spatial payload support).
 * Manages chat messages, loading state, and ORCA companion state.
 * Passes spatial payload from backend response through to ChatMessage objects.
 */
import { useState, useCallback, useRef } from 'react';
import { chatService } from '../services/chatService';
import { initialChatState } from '../store/chatStore';

export function useChat(options = {}) {
  const [messages, setMessages] = useState(initialChatState.messages);
  const [isLoading, setIsLoading] = useState(false);
  const [companionState, setCompanionState] = useState('idle');
  const [error, setError] = useState(null);
  const [activeReasoningSteps, setActiveReasoningSteps] = useState([]);

  const resetTimerRef = useRef(null);
  const sessionIdRef = useRef(`orca-sess-${Date.now()}`);

  const setCompanionStateWithTimeout = useCallback((state, durationMs = 4000) => {
    if (resetTimerRef.current) {
      clearTimeout(resetTimerRef.current);
      resetTimerRef.current = null;
    }
    setCompanionState(state);
    if (state === 'answering' || state === 'error') {
      resetTimerRef.current = window.setTimeout(() => {
        setCompanionState('idle');
      }, durationMs);
    }
  }, []);

  const sendMessage = useCallback(
    async (text, overrideLat, overrideLon) => {
      if (!text || !text.trim()) return;

      let locToSend = options.locationContext;
      if (typeof overrideLat === 'number' && typeof overrideLon === 'number') {
        locToSend = { latitude: overrideLat, longitude: overrideLon };
      } else if (overrideLat && typeof overrideLat === 'object') {
        locToSend = overrideLat;
      }

      const userMessage = {
        id: `usr-${Date.now()}`,
        role: 'user',
        content: text,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // If Offline Safety Mode is active, respond locally without making ANY network calls
      if (options.isOffline) {
        setIsLoading(false);
        const evalInfo = options.offlineSafetyEval;
        const safetySummary = evalInfo
          ? `Status: ${evalInfo.state} · Distance: ${evalInfo.distanceToBoundaryKm?.toFixed(2) || '0.00'} km to ${evalInfo.nearestBoundaryName || 'demarcation'}\nAlert: ${evalInfo.alertMessage || ''}`
          : 'Local geofence safety engine is monitoring vessel position.';

        const offlineNotice = {
          id: `ast-${Date.now()}`,
          role: 'assistant',
          userQuery: text,
          content: `🔴 [OFFLINE SAFETY MODE ACTIVE]\n\nExternal AI agents and online APIs are unavailable while disconnected.\n\n${safetySummary}\n\nLocal GPS tracking and boundary safety checks continue running 100% offline.`,
          timestamp: new Date().toISOString(),
          decision: {
            label: evalInfo?.state === 'BREACH' ? 'Avoid' : evalInfo?.state === 'WARNING' ? 'Operational caution' : 'Clear',
            summary: evalInfo?.alertMessage || 'Offline safety monitoring active.',
            confidence: 'high',
          },
          risk_level: evalInfo?.state === 'BREACH' ? 'critical' : evalInfo?.state === 'WARNING' ? 'high' : 'low',
          risk_summary: evalInfo?.alertMessage || 'Local geofence monitoring.',
          key_conditions: [
            `Current distance: ${evalInfo?.distanceToBoundaryKm?.toFixed(2) || 'N/A'} km to boundary`,
            `Status: ${evalInfo?.state || 'NORMAL'}`,
          ],
          recommendations: evalInfo?.state === 'BREACH'
            ? ['TURN BACK IMMEDIATELY. You have breached maritime demarcation limits.']
            : ['Maintain continuous watch and follow standard safety practices.'],
          best_time: {
            available: false,
            window: null,
            basis: 'Offline Mode: live forecasts unavailable while disconnected.',
          },
          reasoning_summary: 'Why: Offline safety engine evaluated boundary proximity locally without network connectivity.',
          evidence: ['Local geofence dataset (offline)'],
          data_limitations: ['Operating in 100% offline safety mode. External AI agents and online APIs disabled.'],
          agents_used: ['LocalGeofenceEngine'],
        };

        setMessages((prev) => [...prev, offlineNotice]);
        setCompanionStateWithTimeout('answering', 3500);
        return;
      }

      setIsLoading(true);
      setCompanionState('thinking');
      setError(null);

      try {
        const response = await chatService.sendQuery({
          query: text,
          location: locToSend,
          session_id: sessionIdRef.current,
        });

        if (response && response.answer) {
          const assistantMessage = {
            id: `ast-${Date.now()}`,
            role: 'assistant',
            userQuery: text,
            content: response.answer,
            location: response.location,
            mode: response.mode || 'marine',
            timestamp: new Date().toISOString(),
            decision: response.decision,
            risk_level: response.risk_level,
            risk_summary: response.risk_summary,
            key_conditions: response.key_conditions,
            recommendations: response.recommendations,
            suggested_actions: response.recommendations,
            best_time: response.best_time,
            reasoning_summary: response.reasoning_summary,
            evidence: response.evidence,
            structured_evidence: response.structured_evidence,
            data_limitations: response.data_limitations,
            agents_used: response.agents_used,
            spatial: response.spatial || null,
          };
          setActiveReasoningSteps(response.reasoning_steps || []);
          setMessages((prev) => [...prev, assistantMessage]);
          setCompanionStateWithTimeout('answering', 4500);
        } else {
          throw new Error(response?.message || 'Unable to generate reasoning response.');
        }
      } catch (err) {
        const errorText =
          err instanceof Error && err.message && !err.message.includes('Failed to fetch')
            ? `Unable to reach ORCA backend: ${err.message}`
            : 'Unable to reach ORCA backend. Please make sure the ORCA server is running.';

        const errorMessage = {
          id: `ast-${Date.now()}`,
          role: 'assistant',
          content: errorText,
          timestamp: new Date().toISOString(),
          decision: {
            label: 'Connection Error',
            summary: errorText,
            confidence: 'low',
          },
        };

        setError(errorText);
        setMessages((prev) => [...prev, errorMessage]);
        setCompanionStateWithTimeout('error', 4500);
      } finally {
        setIsLoading(false);
      }
    },
    [options.isOffline, options.offlineSafetyEval, options.locationContext, setCompanionStateWithTimeout]
  );

  const clearChat = useCallback(() => {
    setMessages(initialChatState.messages);
    setActiveReasoningSteps([]);
    setError(null);
    setCompanionState('idle');
  }, []);

  return {
    messages,
    isLoading,
    companionState,
    setCompanionState,
    setCompanionStateWithTimeout,
    activeReasoningSteps,
    error,
    sendMessage,
    clearChat,
  };
}

export default useChat;
