import Face from "./Face.jsx";
import { withBdi } from "./Chat.jsx";

// comes with each /chat answer, no model call
export default function Mistakes({ mistakes, onAsk, onPractice }) {
  const learned = mistakes.filter((m) => m.learned).length;

  if (!mistakes.length) {
    return (
      <div className="mistakes-empty">
        <Face mood="smiling" size={64} />
        <p>No mistakes yet. Write a few sentences in the chat and they show up here.</p>
      </div>
    );
  }

  return (
    <section className="mistakes">
      <p className="mistakes-sum">
        {mistakes.length} {mistakes.length === 1 ? "mistake" : "mistakes"} · {learned} learned
      </p>
      <ul>
        {mistakes.map((m) => (
          <li key={m.wrong} className={m.learned ? "is-learned" : ""}>
            <div className="pair">
              <del>{m.wrong}</del> → <em>{m.correct}</em>
            </div>
            <div className="why">
              {m.reason_en && <p className="reason">{m.reason_en}</p>}
              <p className="ar" dir="rtl" lang="ar">
                {withBdi(m.explanation_ar)}
              </p>
              {m.sentence && <p className="from">From: “{m.sentence}”</p>}
            </div>
            <div className="side">
              <span className={"status" + (m.learned ? " ok" : "")}>{m.learned ? "Learned" : "Practicing"}</span>
              {!m.learned && (
                <button
                  className="ask-btn"
                  onClick={() => onPractice({ sentence: m.sentence || "", wrong: m.wrong, correct: m.correct })}
                >
                  Practice it →
                </button>
              )}
              <button
                className="link-btn"
                onClick={() => onAsk({ sentence: m.sentence || "", wrong: m.wrong, correct: m.correct })}
              >
                Ask Maher why →
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
