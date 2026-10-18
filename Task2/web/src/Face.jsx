// Maher's face: م in a circle, eyes above, red mouth. 5 moods.

const INK = "var(--ink)";
const RED = "var(--red)";
const line = (color, w) => ({
  fill: "none",
  stroke: color,
  strokeWidth: w,
  strokeLinecap: "round",
  strokeLinejoin: "round",
});

function Eyes({ mood }) {
  if (mood === "veryHappy") {
    return <path d="M39.5 29q4.5-6.5 9 0M55.5 29q4.5-6.5 9 0" {...line(INK, 3.6)} />;
  }
  if (mood === "disappointed") {
    // half closed: a lid and half an eye
    return (
      <>
        <path d="M39 26.5h10M55 26.5h10" {...line(INK, 2.6)} />
        <path d="M40.3 26.5a3.7 3.7 0 0 0 7.4 0zM56.3 26.5a3.7 3.7 0 0 0 7.4 0z" fill={INK} />
      </>
    );
  }
  const y = mood === "sad" ? 28.5 : 27;
  return (
    <>
      <circle cx="44" cy={y} r="3.8" fill={INK} />
      <circle cx="60" cy={y} r="3.8" fill={INK} />
      {mood === "sad" && <path d="M38 21.5l9.5-3M56.5 18.5l9.5 3" {...line(INK, 2.4)} />}
    </>
  );
}

function Mouth({ mood }) {
  switch (mood) {
    case "smiling":
      return (
        <>
          <path d="M25 75q24 16 47-1" {...line(RED, 6)} />
          <circle cx="73" cy="73.5" r="4.6" fill={RED} />
        </>
      );
    case "sad":
      return (
        <>
          <path d="M27 85q23-14 45 0" {...line(RED, 6)} />
          <circle cx="73" cy="85.5" r="4.6" fill={RED} />
        </>
      );
    case "veryHappy":
      return <path d="M25 71q25 30 50 0z" fill={RED} {...line(RED, 4)} />;
    case "disappointed":
      return <path d="M35 85h30" {...line(RED, 5.5)} />;
    default:
      return (
        <>
          <path d="M26 80h45" {...line(RED, 6)} />
          <circle cx="72.5" cy="80" r="4.6" fill={RED} />
        </>
      );
  }
}

// light colors, so the eyes and red mouth stay clear
const FILL = {
  neutral: "var(--paper)",
  smiling: "#faebb8",
  sad: "#f3cfc9",
  veryHappy: "#f7dc8a",
  disappointed: "#cfddee",
};

const LABEL = {
  neutral: "Maher",
  smiling: "Maher is smiling",
  sad: "Maher looks a bit sad",
  veryHappy: "Maher is very happy",
  disappointed: "Maher looks disappointed",
};

// plain = no mood color (the logo)
export default function Face({ mood = "neutral", size = 56, label = true, plain = false }) {
  return (
    <svg
      className="face"
      width={size}
      height={size}
      viewBox="0 0 100 100"
      {...(label ? { role: "img", "aria-label": LABEL[mood] } : { "aria-hidden": true })}
    >
      <circle
        className="face-bg"
        cx="50"
        cy="50"
        r="46"
        fill={plain ? "var(--paper)" : FILL[mood] || FILL.neutral}
        stroke={INK}
        strokeWidth="4.5"
      />
      {/* the م: a ring and its tail */}
      <circle cx="58" cy="51" r="10.5" {...line(INK, 7.5)} />
      <path d="M47.5 51H37.5q-5 0-5 5v11" {...line(INK, 7.5)} />
      <g key={mood} className="face-part">
        <Eyes mood={mood} />
        <Mouth mood={mood} />
      </g>
    </svg>
  );
}
