import { useState, useCallback, useRef, useEffect } from 'react';
import { ChatMessage, LocationContext, OrcaCompanionState } from '../types/chat.types';
import { DestinationPoint } from '../types/map.types';
import { chatService } from '../services/chatService';
import { initialChatState } from '../store/chatStore';
import { GeofenceEvaluation } from '../services/offlineSafetyService';

interface UseChatOptions {
  onRouteGenerated?: (destination: DestinationPoint) => void;
  isOffline?: boolean;
  offlineSafetyEval?: GeofenceEvaluation;
  locationContext?: LocationContext | null;
}

export function useChat(options: UseChatOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialChatState.messages);
  const messagesRef = useRef<ChatMessage[]>(messages);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [companionState, setCompanionState] = useState<OrcaCompanionState>('idle');
  const [error, setError] = useState<string | null>(null);

  const resetTimerRef = useRef<number | null>(null);
  const sessionIdRef = useRef<string>(`orca-sess-${Date.now()}`);

  const setCompanionStateWithTimeout = useCallback((state: OrcaCompanionState, durationMs = 4000) => {
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
    async (text: string, overrideLocation?: LocationContext | null) => {
      if (!text.trim()) return;

      const locToSend = overrideLocation !== undefined ? overrideLocation : options.locationContext;

      const userMessage: ChatMessage = {
        id: `usr-${Date.now()}`,
        role: 'user',
        content: text,
        location: locToSend || undefined,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // If Offline Safety Mode is active, respond locally without making ANY network calls
      if (options.isOffline) {
        setIsLoading(false);
        const evalInfo = options.offlineSafetyEval;
        const safetySummary = evalInfo
          ? `Status: ${evalInfo.state} · Distance: ${evalInfo.distanceToBoundaryKm.toFixed(2)} km to ${evalInfo.nearestBoundaryName}\nAlert: ${evalInfo.alertMessage}`
          : 'Local geofence safety engine is monitoring vessel position.';

        const offlineNotice: ChatMessage = {
          id: `ast-${Date.now()}`,
          role: 'assistant',
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
            `Current distance: ${evalInfo?.distanceToBoundaryKm.toFixed(2) || 'N/A'} km to boundary`,
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
        // Format recent messages as conversation history for contextual follow-up (using messagesRef to avoid stale closure)
        const conversation_history = messagesRef.current.slice(-6).map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const response = await chatService.sendQuery({
          query: text,
          location: locToSend,
          session_id: sessionIdRef.current,
          conversation_history,
        });

        if (response && response.answer) {
          const sanitizeMarkerTokens = (str?: string | null): string => {
            if (!str || typeof str !== 'string') return '';
            return str.replace(/\bsvg(?=[A-Z])/g, '').trim();
          };

          const sanitizedDecision = response.decision
            ? {
                ...response.decision,
                label: sanitizeMarkerTokens(response.decision.label),
                summary: response.decision.summary ? sanitizeMarkerTokens(response.decision.summary) : undefined,
              }
            : undefined;

          const assistantMessage: ChatMessage = {
            id: `ast-${Date.now()}`,
            role: 'assistant',
            content: sanitizeMarkerTokens(response.answer),
            location: response.location,
            user_location: response.user_location,
            query_location: response.query_location,
            mode: response.mode || 'marine',
            timestamp: new Date().toISOString(),
            decision: sanitizedDecision,
            risk_level: response.risk_level,
            risk_summary: sanitizeMarkerTokens(response.risk_summary) || undefined,
            key_conditions: response.key_conditions?.map((c) => sanitizeMarkerTokens(c)),
            recommendations: response.recommendations?.map((r) => sanitizeMarkerTokens(r)),
            suggested_actions: response.recommendations?.map((r) => sanitizeMarkerTokens(r)),
            best_time: response.best_time,
            reasoning_summary: sanitizeMarkerTokens(response.reasoning_summary) || undefined,
            evidence: response.evidence,
            structured_evidence: response.structured_evidence,
            data_limitations: response.data_limitations?.map((l) => sanitizeMarkerTokens(l)),
            agents_used: response.agents_used,
            human_response: response.human_response,
            spatial: response.spatial,
          };
          setMessages((prev) => [...prev, assistantMessage]);
          setCompanionStateWithTimeout('answering', 4500);
        } else {
          throw new Error('No answer received from ORCA backend.');
        }
      } catch (err: unknown) {
        // Clean error message without fake PFZ or route attachments
        const errorText =
          err instanceof Error && err.message && !err.message.includes('Failed to fetch')
            ? `Unable to reach ORCA backend: ${err.message}`
            : 'Unable to reach ORCA backend. Please make sure the ORCA server is running.';

        const errorMessage: ChatMessage = {
          id: `ast-${Date.now()}`,
          role: 'assistant',
          content: errorText,
          timestamp: new Date().toISOString(),
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
    setError(null);
    setCompanionState('idle');
    sessionIdRef.current = `orca-sess-${Date.now()}`;
  }, []);

  return {
    messages,
    isLoading,
    companionState,
    setCompanionState,
    setCompanionStateWithTimeout,
    error,
    sendMessage,
    clearChat,
  };
}
