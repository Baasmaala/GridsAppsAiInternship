import { useState } from "react";
import Face from "./Face.jsx";
import Hear from "./Hear.jsx";
import Mic from "./Mic.jsx";
import { withBdi } from "./Chat.jsx";

export const SUGGESTIONS = ["Explain past simple", 'When do I use "an"?', "Can you give me a quick test?"];

// old saved answers have no suggestions, they get these
const OLD_FOLLOW_UPS = ["Simpler please", "More examples", "Test me"];

const ERRORS = {
  busy: "I'm a bit busy right now. Ask me again in a moment.",
  offline: "I can't hear you. Is the API running?",
  limit: "That's all for today. Ask me again tomorrow.",
};

function Answer({ msg, last, onFollow, busy }) {
  const { data } = msg;
  return (
    <div className="ask-maher">
      <div className="label">
        <Face mood={data?.learned ? "veryHappy" : "neutral"} size={18} label={false} />
        Maher
        {data?.learned && <span className="passed">Passed · learned</span>}
      </div>
      {msg.loading && <p className="reading">Thinking…</p>}
      {msg.error && <p className="error-note">{ERRORS[msg.error] || msg.message}</p>}
      {data && (
        <>
          <p className={"ar-answer" + (data.learned ? " ok" : "")} dir="rtl" lang="ar">
            {withBdi(data.answer_ar)}
          </p>
          {data.examples.length > 0 && (
            // whole sentences read better one per line
            <ul className={"examples" + (data.examples.some((x) => (x.before + x.after).length > 24) ? " long" : "")}>
              {data.examples.map((x, i) => (
                <li key={i}>
                  {x.before} → <em>{x.after}</em>
                </li>
              ))}
            </ul>
          )}
          {data.practice && (
            <div className="practice">
              <span className="tag">Practice</span>
              <p>{data.practice}</p>
              <Hear text={data.practice} what="the practice question" />
            </div>
          )}
          {last && (
            <div className="chips follow">
              {(data.suggestions?.length ? data.suggestions : OLD_FOLLOW_UPS).map((s) => (
                <button key={s} className="chip" onClick={() => onFollow(s)} disabled={busy}>
                  {s}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// onClose: close it, or pin it when peeking
export default function AskPanel({ messages, onAsk, waiting, limit, inputRef, scrollRef, onClose, pinned }) {
  const [text, setText] = useState("");
  const [lang, setLang] = useState("en-US"); // mic language: English or Arabic
  const [micError, setMicError] = useState("");
  const lastId = [...messages].reverse().find((m) => m.role === "maher")?.id;

  function send(q) {
    if (!q.trim() || waiting || limit) return;
    onAsk(null, q.trim());
    setText("");
  }

  return (
    <>
      <header className="ask-head">
        <Face mood="neutral" size={34} label={false} plain />
        <div>
          <h2>Ask Maher</h2>
          <p>Grammar questions, any time</p>
        </div>
        {onClose && (
          <button className="ask-close" onClick={onClose}>
            {pinned ? "Close ×" : "Keep open"}
          </button>
        )}
      </header>

      <div className="ask-scroll" ref={scrollRef}>
        <div className="ask-list">
          {messages.length === 0 && (
            <p className="ask-intro">
              Ask me anything about English grammar. Or tap a red correction in your chat and press{" "}
              <em>Ask Maher why</em>.
            </p>
          )}
          {messages.map((m) =>
            m.role === "you" ? (
              <div className="ask-you" key={m.id}>
                {m.context && (
                  <span className="ctx">
                    {m.practice ? "Practice:" : "From your chat:"}{" "}
                  {m.context.correct ? (
                    <>
                      <del>{m.context.wrong}</del> → <em>{m.context.correct}</em>
                    </>
                  ) : (
                    <>
                      <span className="wavy">{m.context.wrong}</span> · fixing
                    </>
                  )}
                  </span>
                )}
                <p className="q">{m.text}</p>
              </div>
            ) : (
              <Answer key={m.id} msg={m} last={m.id === lastId} onFollow={send} busy={waiting || limit} />
            )
          )}
        </div>
      </div>

      <div className="ask-foot">
        {messages.length === 0 && (
          <div className="chips">
            {SUGGESTIONS.map((s) => (
              <button key={s} className="chip" onClick={() => send(s)} disabled={waiting || limit}>
                {s}
              </button>
            ))}
          </div>
        )}
        {micError && <p className="mic-error">{micError}</p>}
        <form
          className="ask-form"
          onSubmit={(ev) => {
            ev.preventDefault();
            send(text);
          }}
        >
          <input
            ref={inputRef}
            value={text}
            onChange={(ev) => setText(ev.target.value)}
            placeholder={limit ? "Back tomorrow" : "Ask about grammar…"}
            maxLength={500}
            disabled={limit}
            aria-label="Your grammar question"
            autoComplete="off"
            dir="auto"
          />
          <button
            type="button"
            className="lang"
            onClick={() => setLang((l) => (l === "en-US" ? "ar" : "en-US"))}
            aria-label={lang === "ar" ? "Mic language: Arabic. Switch to English" : "Mic language: English. Switch to Arabic"}
            title="Mic language"
          >
            {lang === "ar" ? "ع" : "EN"}
          </button>
          <Mic lang={lang} value={text} onText={setText} onError={setMicError} disabled={waiting || limit} />
          <button className="ask-send" disabled={waiting || limit || !text.trim()} aria-label="Ask">
            →
          </button>
        </form>
      </div>
    </>
  );
}
