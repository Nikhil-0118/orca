/**
 * Browser Audio Buzzer Service for ORCA Offline Boat Safety Simulator.
 *
 * Synthesizes an actual maritime emergency alarm using HTML5 Web Audio API.
 * 100% offline, zero external audio files, zero network dependencies.
 *
 * Capabilities:
 * - Single active alarm loop (isAlarmActive state tracking) to prevent overlapping audio
 * - Does not restart audio on every position or drag event
 * - Handles browser autoplay restrictions gracefully via unlockAudio()
 * - Automatic start on DANGER condition, automatic stop when returning to SAFE / CAUTION
 * - One-shot caution alert chime on entering CAUTION zone
 * - Clean mute / unmute toggle and resource disposal
 */

export interface BuzzerState {
  isAlarmActive: boolean;
  isAudioUnlocked: boolean;
  isMuted: boolean;
}

type BuzzerListener = (state: BuzzerState) => void;

class BuzzerService {
  private audioCtx: AudioContext | null = null;
  private isAlarmActive: boolean = false;
  private isAudioUnlocked: boolean = false;
  private isMuted: boolean = false;
  private alarmInterval: number | null = null;
  private listeners: Set<BuzzerListener> = new Set();
  private lastBeepHigh = false;

  private notify(): void {
    const state = this.getState();
    this.listeners.forEach((listener) => {
      try {
        listener(state);
      } catch (err) {
        console.error('[BuzzerService] Listener error:', err);
      }
    });
  }

  public subscribe(listener: BuzzerListener): () => void {
    this.listeners.add(listener);
    listener(this.getState());
    return () => {
      this.listeners.delete(listener);
    };
  }

  public getState(): BuzzerState {
    return {
      isAlarmActive: this.isAlarmActive,
      isAudioUnlocked: this.isAudioUnlocked,
      isMuted: this.isMuted,
    };
  }

  /**
   * Initializes or resumes the AudioContext on user interaction.
   * Browsers require a user gesture before Web Audio can emit sound.
   */
  public async unlockAudio(): Promise<boolean> {
    try {
      if (typeof window === 'undefined') return false;
      if (!this.audioCtx) {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          this.audioCtx = new AudioCtx();
        }
      }
      if (this.audioCtx && this.audioCtx.state === 'suspended') {
        await this.audioCtx.resume();
      }
      this.isAudioUnlocked = !!(this.audioCtx && this.audioCtx.state === 'running');
      this.notify();
      return this.isAudioUnlocked;
    } catch (e) {
      console.warn('[BuzzerService] Failed to unlock audio context:', e);
      return false;
    }
  }

  public setMuted(muted: boolean): void {
    this.isMuted = muted;
    if (muted && this.isAlarmActive) {
      this.stopAlarmLoop();
    } else if (!muted && this.isAlarmActive) {
      this.startAlarmLoop();
    }
    this.notify();
  }

  public toggleMute(): boolean {
    this.setMuted(!this.isMuted);
    return this.isMuted;
  }

  /**
   * Starts the continuous danger buzzer.
   * Idempotent: If alarm is already active, this is a NO-OP to prevent
   * overlapping audio instances or restarts on continuous drag movements.
   */
  public startDangerAlarm(): void {
    if (this.isAlarmActive) {
      return;
    }
    this.isAlarmActive = true;
    this.notify();

    if (!this.isMuted) {
      this.startAlarmLoop();
    }
  }

  /**
   * Stops the buzzer immediately when vessel returns to safe state.
   */
  public stopDangerAlarm(): void {
    if (!this.isAlarmActive) {
      return;
    }
    this.isAlarmActive = false;
    this.stopAlarmLoop();
    this.notify();
  }

  /**
   * Plays a single one-shot warning chime when entering CAUTION zone.
   */
  public playCautionWarning(): void {
    if (this.isMuted || !this.audioCtx) return;
    try {
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume().catch(() => {});
      }
      const now = this.audioCtx.currentTime;
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.setValueAtTime(783.99, now + 0.12); // G5

      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.28);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc.start(now);
      osc.stop(now + 0.3);
    } catch {
      // Browser autoplay restriction before first interaction
    }
  }

  private startAlarmLoop(): void {
    this.stopAlarmLoop();
    this.playSingleAlarmPulse();
    // Urgent repeating siren cadence: pulses every 280ms
    this.alarmInterval = setInterval(() => {
      this.playSingleAlarmPulse();
    }, 280) as unknown as number;
  }

  private stopAlarmLoop(): void {
    if (this.alarmInterval !== null) {
      clearInterval(this.alarmInterval);
      this.alarmInterval = null;
    }
  }

  private playSingleAlarmPulse(): void {
    if (this.isMuted || !this.isAlarmActive) return;
    if (!this.audioCtx) {
      this.unlockAudio();
      return;
    }
    try {
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume().catch(() => {});
      }
      const now = this.audioCtx.currentTime;
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      // Alternating urgent two-tone emergency buzzer (940 Hz & 740 Hz)
      this.lastBeepHigh = !this.lastBeepHigh;
      const freq = this.lastBeepHigh ? 940 : 740;

      osc.type = 'sawtooth'; // Piercing buzzer timbre
      osc.frequency.setValueAtTime(freq, now);

      gain.gain.setValueAtTime(0.28, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.22);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc.start(now);
      osc.stop(now + 0.24);
    } catch (e) {
      console.warn('[BuzzerService] Audio pulse error:', e);
    }
  }

  public dispose(): void {
    this.stopDangerAlarm();
    if (this.audioCtx && this.audioCtx.state !== 'closed') {
      this.audioCtx.close().catch(() => {});
      this.audioCtx = null;
    }
    this.listeners.clear();
  }
}

export const buzzerService = new BuzzerService();
