// read aloud with the browser voice, no model call
// one male English voice, tone follows his face

export const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window;

export const TONES = {
  neutral: { pitch: 1.0, rate: 1.0, label: "Neutral" },
  smiling: { pitch: 1.15, rate: 1.05, label: "Cheerful" },
  sad: { pitch: 0.85, rate: 0.9, label: "A bit sad" },
  veryHappy: { pitch: 1.3, rate: 1.12, label: "Very happy" },
  disappointed: { pitch: 0.8, rate: 0.85, label: "Disappointed" },
};

// browsers don't say which voice is male, so look at the names
const MALE = ["guy", "christopher", "eric", "roger", "andrew", "brian", "davis", "tony",
  "jason", "david", "mark", "george", "james", "ryan", "thomas", "daniel", "alex", "fred",
  "aaron", "arthur", "google uk english male"];
let maher = null;

function maherVoice() {
  if (maher) return maher;
  const en = speechSynthesis
    .getVoices()
    .filter((v) => /^en[-_](us|gb)/i.test(v.lang))
    .sort((a, b) => /us/i.test(b.lang) - /us/i.test(a.lang)); // en-US first
  maher = en.find((v) => MALE.some((n) => v.name.toLowerCase().includes(n))) || en[0] || null;
  return maher;
}

if (canSpeak) {
  // some browsers load the voices late
  speechSynthesis.addEventListener?.("voiceschanged", maherVoice);
}

export function speak(text, tone = "neutral") {
  if (!canSpeak || !text) return;
  speechSynthesis.cancel(); // never two at the same time
  const t = TONES[tone] || TONES.neutral;
  const u = new SpeechSynthesisUtterance(text);
  const voice = maherVoice();
  if (voice) u.voice = voice;
  u.lang = voice?.lang || "en-US";
  u.pitch = t.pitch;
  u.rate = t.rate;
  speechSynthesis.speak(u);
}
