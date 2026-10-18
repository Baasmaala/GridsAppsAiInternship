import { useEffect, useRef, useState } from "react";

// browser speech to text (Chrome, Edge), no model call
const Rec = typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);

const ERRORS = {
  "not-allowed": "The mic is blocked. Allow it in the browser.",
  "service-not-allowed": "The mic is blocked. Allow it in the browser.",
  "no-speech": "I didn't hear anything. Try again.",
  "audio-capture": "No mic found.",
  network: "Voice needs the internet.",
};

// value = what is in the input now, the voice text goes after it
export default function Mic({ lang = "en-US", value, onText, onError, disabled }) {
  const [on, setOn] = useState(false);
  const rec = useRef(null);

  useEffect(() => () => rec.current?.abort(), []);

  if (!Rec) return null;

  function toggle() {
    if (on) {
      rec.current?.stop();
      return;
    }
    const r = new Rec();
    r.lang = lang;
    r.interimResults = true; // the text shows while you talk
    r.continuous = false;
    const base = value.trim() ? value.trimEnd() + " " : "";
    r.onresult = (ev) => {
      let said = "";
      for (const res of ev.results) said += res[0].transcript;
      onText(base + said.trim());
    };
    r.onerror = (ev) => ev.error !== "aborted" && onError?.(ERRORS[ev.error] || "Voice didn't work. Try again.");
    r.onend = () => setOn(false);
    rec.current = r;
    onError?.("");
    r.start();
    setOn(true);
  }

  return (
    <button
      type="button"
      className={"mic" + (on ? " on" : "")}
      onClick={toggle}
      disabled={disabled}
      aria-pressed={on}
      aria-label={on ? "Stop listening" : "Speak instead of typing"}
      title={on ? "Listening… click to stop" : "Speak"}
    >
      <svg width="16" height="16" viewBox="0 0 20 20" aria-hidden="true">
        <rect x="7" y="2.5" width="6" height="10" rx="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
        <path d="M4.5 9.5a5.5 5.5 0 0 0 11 0M10 15v2.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    </button>
  );
}
