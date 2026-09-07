import React from 'react';
import { Mic, X, AlertCircle, Sparkles, Send } from 'lucide-react';
import { OrcaWaveform } from './OrcaWaveform';

interface OrcaVoiceOverlayProps {
  isOpen: boolean;
  isListening: boolean;
  transcript: string;
  audioLevel: number;
  error: string | null;
  onClose: () => void;
  onSend: (text: string) => void;
  onRetry: () => void;
}

export const OrcaVoiceOverlay: React.FC<OrcaVoiceOverlayProps> = ({
  isOpen,
  isListening,
  transcript,
  audioLevel,
  error,
  onClose,
  onSend,
  onRetry,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-md rounded-3xl bg-slate-900/95 border border-cyan-500/40 p-6 shadow-2xl shadow-cyan-950/80 flex flex-col items-center text-center space-y-5">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors"
          aria-label="Close voice search"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Pulse Mic Orb */}
        <div className="relative mt-2 flex items-center justify-center">
          {isListening && (
            <>
              <div className="absolute w-24 h-24 rounded-full bg-cyan-500/20 animate-ping"></div>
              <div className="absolute w-32 h-32 rounded-full border border-cyan-400/30 animate-pulse"></div>
            </>
          )}
          <div
            className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-xl transition-all duration-300 ${
              isListening
                ? 'bg-gradient-to-tr from-cyan-500 to-blue-600 text-navy-950 shadow-cyan-500/40 scale-110'
                : error
                ? 'bg-red-950 border border-red-500 text-red-300'
                : 'bg-slate-800 text-slate-300'
            }`}
          >
            <Mic className="w-8 h-8 animate-pulse" />
          </div>
        </div>

        {/* Status Heading */}
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 text-xs font-mono">
            <Sparkles className="w-3 h-3 text-cyan-400" />
            <span>ORCA Voice Assistant</span>
          </div>
          <h3 className="text-lg font-bold text-slate-100">
            {isListening ? 'ORCA is Listening...' : error ? 'Voice Search Status' : 'Processing Query...'}
          </h3>
          <p className="text-xs text-slate-400">
            {isListening
              ? 'Speak naturally (e.g., "Is it safe to fish tomorrow near Chennai?")'
              : error
              ? 'Please see the fallback below.'
              : 'Captured speech.'}
          </p>
        </div>

        {/* Audio Waveform */}
        {isListening && (
          <div className="w-full">
            <OrcaWaveform isListening={isListening} audioLevel={audioLevel} barCount={24} />
          </div>
        )}

        {/* Live Transcript Box */}
        {transcript && (
          <div className="w-full p-4 rounded-2xl bg-navy-950/90 border border-cyan-900/50 text-sm text-cyan-100 font-medium text-left shadow-inner">
            <span className="text-[10px] font-mono text-cyan-400 uppercase block mb-1">Live Transcript</span>
            <p className="italic">"{transcript}"</p>
          </div>
        )}

        {/* Error / Fallback Banner */}
        {error && (
          <div className="w-full p-3.5 rounded-2xl bg-red-950/60 border border-red-800/80 text-xs text-red-200 flex items-start gap-2.5 text-left">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold block">{error}</span>
              <span className="text-slate-400 block text-[11px]">
                You can use the chat text box directly to type your question.
              </span>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2 w-full justify-center">
          {error ? (
            <>
              <button
                onClick={onRetry}
                className="px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
              >
                Type Question Instead
              </button>
            </>
          ) : (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
              >
                Cancel
              </button>
              {transcript && (
                <button
                  onClick={() => {
                    onSend(transcript);
                    onClose();
                  }}
                  className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-navy-950 font-bold text-xs flex items-center gap-1.5 shadow-lg shadow-cyan-500/20"
                >
                  <span>Send Question</span>
                  <Send className="w-3.5 h-3.5" />
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
