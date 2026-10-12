import { useState } from "react";
import { Volume2, VolumeX } from "lucide-react";
import { setSoundEnabled, soundEnabled, unlockSound } from "../../../lib/sound";
import styles from "./SoundToggle.module.css";

/**
 * Browsers keep a page silent until the visitor clicks something. This button is that
 * click: it switches the illustration sounds on (or off) and is remembered on this device.
 */
export function SoundToggle() {
  const [on, setOn] = useState(soundEnabled);
  const [unlocked, setUnlocked] = useState(false);
  const active = on && unlocked;

  const toggle = () => {
    unlockSound();
    const next = !active;
    setSoundEnabled(next);
    setOn(next);
    setUnlocked(true);
  };

  return (
    <button
      type="button"
      className={active ? `${styles.toggle} ${styles.on}` : styles.toggle}
      onClick={toggle}
      aria-pressed={active}
      aria-label={active ? "Sound effects on. Turn off" : "Turn on sound effects"}
      title={active ? "Sound effects on" : "Hover the illustrations to hear them"}
    >
      {active ? <Volume2 size={18} aria-hidden="true" /> : <VolumeX size={18} aria-hidden="true" />}
      <span className={styles.label}>{active ? "Sound on" : "Sound"}</span>
    </button>
  );
}
