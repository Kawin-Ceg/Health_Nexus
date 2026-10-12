/**
 * Small interface sounds, synthesised with Web Audio so there are no files to load.
 * Off switch is per device (localStorage). Browsers only allow audio after the person
 * has interacted with the page, so a sound that cannot start is simply skipped.
 */

export type Sound = "alert" | "clear" | "message";

const KEY = "hn.sound";
let ctx: AudioContext | null = null;

export function soundEnabled(): boolean {
  try {
    return localStorage.getItem(KEY) !== "off";
  } catch {
    return true;
  }
}

export function setSoundEnabled(on: boolean) {
  try {
    localStorage.setItem(KEY, on ? "on" : "off");
  } catch {
    // Storage blocked (private mode): the choice lasts for this page only.
  }
  if (on) play("message");
}

const NOTES: Record<Sound, { freq: number; at: number; length: number }[]> = {
  alert: [
    { freq: 659.25, at: 0, length: 0.16 },
    { freq: 987.77, at: 0.14, length: 0.26 },
  ],
  clear: [
    { freq: 1046.5, at: 0, length: 0.1 },
    { freq: 1318.5, at: 0.07, length: 0.1 },
    { freq: 1568, at: 0.14, length: 0.2 },
  ],
  message: [{ freq: 740, at: 0, length: 0.14 }],
};

export function play(sound: Sound) {
  if (!soundEnabled() || typeof window === "undefined" || !("AudioContext" in window)) return;
  ctx ??= new AudioContext();
  if (ctx.state === "suspended") void ctx.resume().catch(() => undefined);
  if (ctx.state !== "running" && ctx.state !== "suspended") return;
  const now = ctx.currentTime + 0.01;
  for (const note of NOTES[sound]) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(note.freq, now + note.at);
    if (sound === "message") osc.frequency.exponentialRampToValueAtTime(note.freq * 1.35, now + note.at + note.length);
    gain.gain.setValueAtTime(0.0001, now + note.at);
    gain.gain.exponentialRampToValueAtTime(0.08, now + note.at + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + note.at + note.length);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now + note.at);
    osc.stop(now + note.at + note.length + 0.02);
  }
}

function ready(): AudioContext | null {
  if (!soundEnabled() || typeof window === "undefined" || !("AudioContext" in window)) return null;
  ctx ??= new AudioContext();
  return ctx.state === "running" ? ctx : null;
}

let noiseBuffer: AudioBuffer | null = null;

function tone(
  ac: AudioContext,
  at: number,
  length: number,
  freq: number,
  { type = "sine", volume = 0.03, to }: { type?: OscillatorType; volume?: number; to?: number } = {},
) {
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, at);
  if (to) osc.frequency.exponentialRampToValueAtTime(to, at + length);
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.exponentialRampToValueAtTime(volume, at + Math.min(0.012, length / 4));
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
  osc.connect(gain).connect(ac.destination);
  osc.start(at);
  osc.stop(at + length + 0.02);
}

function noise(ac: AudioContext, at: number, length: number, filter: BiquadFilterType, freq: number, volume = 0.03, q = 1) {
  if (!noiseBuffer) {
    noiseBuffer = ac.createBuffer(1, ac.sampleRate, ac.sampleRate);
    const data = noiseBuffer.getChannelData(0);
    for (let i = 0; i < data.length; i += 1) data[i] = Math.random() * 2 - 1;
  }
  const src = ac.createBufferSource();
  const band = ac.createBiquadFilter();
  const gain = ac.createGain();
  src.buffer = noiseBuffer;
  band.type = filter;
  band.frequency.setValueAtTime(freq, at);
  band.Q.value = q;
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.exponentialRampToValueAtTime(volume, at + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
  src.connect(band).connect(gain).connect(ac.destination);
  src.start(at);
  src.stop(at + length + 0.02);
}

function wobble(ac: AudioContext, at: number, length: number, freq: number, rate: number, depth: number, volume = 0.025) {
  const osc = ac.createOscillator();
  const lfo = ac.createOscillator();
  const lfoGain = ac.createGain();
  const gain = ac.createGain();
  osc.frequency.value = freq;
  lfo.frequency.value = rate;
  lfoGain.gain.value = depth;
  lfo.connect(lfoGain).connect(osc.frequency);
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.exponentialRampToValueAtTime(volume, at + 0.03);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + length);
  osc.connect(gain).connect(ac.destination);
  osc.start(at);
  lfo.start(at);
  osc.stop(at + length + 0.02);
  lfo.stop(at + length + 0.02);
}

/** A short sound that matches each illustration, played when the cursor reaches it. */
const RECIPES: Record<string, (ac: AudioContext, t: number) => void> = {
  ecg: (ac, t) => {
    tone(ac, t, 0.09, 1000, { volume: 0.025 });
    tone(ac, t + 0.16, 0.09, 1000, { volume: 0.025 });
  },
  beads: (ac, t) => {
    [0, 0.05, 0.12, 0.17].forEach((d, i) => tone(ac, t + d, 0.05, 2400 + i * 380, { type: "triangle", volume: 0.018 }));
  },
  capsules: (ac, t) => {
    [0, 0.04, 0.09, 0.13, 0.2].forEach((d) => noise(ac, t + d, 0.035, "bandpass", 3200, 0.05, 6));
  },
  tree: (ac, t) => {
    [392, 493.88, 587.33].forEach((f, i) => tone(ac, t + i * 0.07, 0.3, f, { type: "triangle", volume: 0.02 }));
  },
  honeycomb: (ac, t) => wobble(ac, t, 0.45, 220, 32, 18, 0.012),
  radial: (ac, t) => {
    [1568, 2093, 2637].forEach((f, i) => tone(ac, t + i * 0.05, 0.4, f, { volume: 0.012 }));
  },
  helix: (ac, t) => tone(ac, t, 0.35, 300, { type: "triangle", volume: 0.02, to: 900 }),
  tissue: (ac, t) => noise(ac, t, 0.25, "lowpass", 500, 0.05),
  network: (ac, t) => {
    [880, 1320, 1100, 1760].forEach((f, i) => tone(ac, t + i * 0.06, 0.05, f, { type: "square", volume: 0.006 }));
  },
  botanical: (ac, t) => noise(ac, t, 0.5, "bandpass", 1800, 0.025, 0.7),
  flask: (ac, t) => {
    [0, 0.09, 0.2].forEach((d, i) => tone(ac, t + d, 0.07, 500 + i * 140, { volume: 0.025, to: 1300 + i * 200 }));
  },
  speckle: (ac, t) => {
    for (let i = 0; i < 7; i += 1) tone(ac, t + i * 0.035, 0.05, 3000 + ((i * 523) % 1800), { volume: 0.008 });
  },
  microbe: (ac, t) => wobble(ac, t, 0.4, 330, 9, 40, 0.02),
  coral: (ac, t) => tone(ac, t, 0.35, 420, { volume: 0.035, to: 140 }),
};

export function illustrationSound(piece: string) {
  const ac = ready();
  if (!ac) return;
  RECIPES[piece]?.(ac, ac.currentTime + 0.005);
}

/** Starts audio. Only works from a click or key press: browsers keep pages silent until then. */
export function unlockSound() {
  if (typeof window === "undefined" || !("AudioContext" in window)) return;
  ctx ??= new AudioContext();
  void ctx.resume().catch(() => undefined);
}

if (typeof window !== "undefined") {
  window.addEventListener("pointerdown", unlockSound, { once: true });
  window.addEventListener("keydown", unlockSound, { once: true });
}
