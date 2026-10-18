import { useEffect, useRef } from "react";
import { canSpeak, speak, TONES } from "./speech.js";

// "HEAR · CHEERFUL" pill. auto = play once by itself (only for new entries)
export default function Hear({ text, tone = "neutral", auto = false, what }) {
  const played = useRef(false);
  useEffect(() => {
    if (auto && text && !played.current) {
      played.current = true;
      speak(text, tone);
    }
  }, [auto, text, tone]);

  if (!canSpeak || !text) return null;
  const name = TONES[tone]?.label || "Neutral";
  return (
    <button
      className="hear"
      onClick={() => speak(text, tone)}
      aria-label={`Listen to ${what || "this"} (${name.toLowerCase()})`}
    >
      <svg width="12" height="12" viewBox="0 0 20 20" aria-hidden="true">
        <path d="M3 7.5h3l4.5-3.5v12L6 12.5H3z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
        <path d="M13.5 7.2c1 .8 1 4.8 0 5.6M15.8 5.2c2 1.9 2 7.7 0 9.6" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
      Hear · {name}
    </button>
  );
}
