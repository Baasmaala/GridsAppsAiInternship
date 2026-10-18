import { Fragment, useEffect, useLayoutEffect, useRef, useState } from "react";
import Face from "./Face.jsx";
import Hear from "./Hear.jsx";

// picked by entry id, so a reload keeps the same line
const LINES = {
  correct: ["Yes! You fixed it.", "That's it, well done.", "Perfect, now it's right."],
  almost: ["Not yet. Look at the hint.", "Close! Read the hint and try again."],
  gave_up: ["Good try. Here it is:", "Nearly. Here's the right one:"],
  skipped: ["OK, we skip this one. Here it is:"],
  fixed_new: ["You fixed it! But there's a new small slip:", "That part is right now! One more thing to fix:"],
};

function pick(list, seed = "") {
  let n = 0;
  for (const c of seed) n += c.charCodeAt(0);
  return list[n % list.length];
}

// same mood for his face and voice
export function entryMood(data) {
  if (!data) return "neutral";
  if (data.kind === "check") return data.errors.length ? "sad" : "smiling";
  return { correct: "veryHappy", almost: "sad", gave_up: "sad", skipped: "disappointed", fixed_new: "sad" }[
    data.status
  ];
}

// English inside Arabic goes in <bdi>, so dots stay in place.
// "play → played" stays one piece.
export function withBdi(text) {
  return text.split(/(\(?[A-Za-z][\w'’-]*(?:[ ,:/→()]+[A-Za-z][\w'’-]*)*\)?)/).map((part, i) =>
    i % 2 ? <bdi key={i}>{part}</bdi> : part
  );
}

// for matching: lowercase, no apostrophes ("Don't" = "dont")
// map[i] = index in the real sentence
function plain(text) {
  let out = "";
  const map = [];
  [...text].forEach((c, i) => {
    if (/['’`]/.test(c)) return;
    out += c.toLowerCase();
    map.push(i);
  });
  return { out, map };
}

// mistakes we can't find go to "missed"
function markSentence(sentence, errors) {
  const { out: lower, map } = plain(sentence);
  const spots = [];
  const missed = [];
  for (const e of errors) {
    const wrong = plain(e.wrong.trim().replace(/^"|"$/g, "")).out;
    let found = null;
    let from = 0;
    let i;
    // first place that doesn't overlap another fix (and is a whole word)
    while (wrong && (i = lower.indexOf(wrong, from)) !== -1) {
      const at = map[i];
      const end = map[i + wrong.length - 1] + 1;
      const wordStart = at === 0 || !/\w/.test(sentence[at - 1]);
      const wordEnd = end === sentence.length || !/\w/.test(sentence[end]);
      const free = spots.every((s) => end <= s.at || at >= s.end);
      if (wordStart && wordEnd && free) {
        found = { at, end };
        break;
      }
      from = i + 1;
    }
    if (!found) missed.push(e);
    else spots.push({ ...found, e });
  }
  spots.sort((a, b) => a.at - b.at);
  return { spots, missed };
}

// dark box: hover, focus or tap
function usePop() {
  const [open, setOpen] = useState(false);
  const [side, setSide] = useState("");
  const ref = useRef(null);

  useLayoutEffect(() => {
    // keep the box inside the chat column
    if (!open) return setSide("");
    const box = ref.current.querySelector(".pop").getBoundingClientRect();
    const col = ref.current.closest(".chat-scroll").getBoundingClientRect();
    if (box.right > col.right - 4) setSide(" to-left");
    else if (box.left < col.left + 4) setSide(" to-right");
  }, [open]);

  useEffect(() => {
    // tap somewhere else closes it (phone)
    if (!open) return;
    const close = (ev) => !ref.current?.contains(ev.target) && setOpen(false);
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);

  const props = {
    ref,
    tabIndex: 0,
    onMouseEnter: () => setOpen(true),
    onMouseLeave: () => setOpen(false),
    onFocus: () => setOpen(true),
    onBlur: (ev) => !ev.currentTarget.contains(ev.relatedTarget) && setOpen(false),
    onClick: () => setOpen(true),
    onKeyDown: (ev) => ev.key === "Escape" && setOpen(false),
  };
  return { open, setOpen, side, props };
}

function Fix({ text, e, order, sentence, onAsk }) {
  const { open, setOpen, side, props } = usePop();
  return (
    <span
      {...props}
      className={"fix" + (open ? " open" : "")}
      style={{ "--i": order }}
      aria-label={`${text}, write ${e.correct}`}
    >
      <del>{text}</del>
      <ins>{e.correct}</ins>
      {open && (
        <span className={"pop" + side} role="tooltip">
          {e.reason_en && <span className="pop-reason">{e.reason_en}</span>}
          <span className="pop-ar" dir="rtl" lang="ar">
            {withBdi(e.explanation_ar)}
          </span>
          <button
            className="pop-ask"
            onClick={(ev) => {
              ev.stopPropagation();
              setOpen(false);
              onAsk({ sentence, wrong: e.wrong, correct: e.correct });
            }}
          >
            Ask Maher why →
          </button>
        </span>
      )}
    </span>
  );
}

// still wrong in the fix step: hint only, never the answer
function StillWrong({ text, hint, sentence, onAsk }) {
  const { open, setOpen, side, props } = usePop();
  return (
    <span {...props} className={"fix still" + (open ? " open" : "")} aria-label={`${text}, still not right`}>
      <span className="wavy">{text}</span>
      {open && (
        <span className={"pop" + side} role="tooltip">
          <span className="pop-reason">Not yet. Here's a hint:</span>
          {hint && (
            <span className="pop-ar" dir="rtl" lang="ar">
              {withBdi(hint)}
            </span>
          )}
          <button
            className="pop-ask"
            onClick={(ev) => {
              ev.stopPropagation();
              setOpen(false);
              onAsk({ sentence, wrong: text, correct: "" });
            }}
          >
            Ask Maher for a hint →
          </button>
        </span>
      )}
    </span>
  );
}

function Tick() {
  return (
    <svg className="tick" width="20" height="16" viewBox="0 0 22 18" role="img" aria-label="correct">
      <path
        d="M2 9.5c2 1.4 3.6 3.2 5 5.6C10 9 14.5 4.2 20.5 1.8"
        pathLength="1"
        fill="none"
        stroke="var(--green)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// action = "Ask Maher" button
export function MaherSays({ mood = "neutral", children, hear, auto, action }) {
  return (
    <div className="msg maher">
      <div className="label">
        <Face mood={mood} size={18} label={false} />
        Maher
      </div>
      <div className="maher-text">{children}</div>
      {(hear || action) && (
        <div className="msg-actions">
          {hear && <Hear text={hear} tone={mood} auto={auto} what="Maher" />}
          {action && (
            <button className="ask-btn" onClick={action.onClick}>
              {action.label}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function YouWrote({ children, hear }) {
  return (
    <div className="msg you">
      <div className="label">You</div>
      <p className="you-text">{children}</p>
      {/* your own sentence, always the neutral voice */}
      {hear && <Hear text={hear} tone="neutral" what="your sentence" />}
    </div>
  );
}

function CheckEntry({ data, onAsk }) {
  const { spots, missed } = markSentence(data.sentence, data.errors);
  const parts = [];
  let pos = 0;
  spots.forEach((s, order) => {
    if (s.at > pos) parts.push(data.sentence.slice(pos, s.at));
    parts.push(
      <Fix
        key={s.at}
        text={data.sentence.slice(s.at, s.end)}
        e={s.e}
        order={order}
        sentence={data.sentence}
        onAsk={onAsk}
      />
    );
    pos = s.end;
  });
  parts.push(data.sentence.slice(pos));

  const ok = data.errors.length === 0;
  const mood = entryMood(data);
  const reminder = data.reminder ? ` Don't forget: say ${data.reminder.correct}, not ${data.reminder.wrong}.` : "";
  // one button for all mistakes (1 question = 1 call)
  const many = data.errors.length > 1;
  const action = ok
    ? null
    : {
        label: many ? "Ask Maher about these →" : "Ask Maher why →",
        onClick: () =>
          onAsk(
            {
              sentence: data.sentence,
              wrong: data.errors.map((e) => e.wrong).join(", "),
              correct: data.errors.map((e) => e.correct).join(", "),
            },
            many ? "Why are these wrong?" : null
          ),
      };
  return (
    <>
      <YouWrote hear={data.sentence}>
        {parts}
        {ok && <Tick />}
      </YouWrote>
      <MaherSays mood={mood} hear={data.reply + reminder} action={action}>
        <p>{data.reply}</p>
        {missed.map((e) => (
          <p className="missed" key={e.wrong}>
            <del>{e.wrong}</del> → <ins>{e.correct}</ins>
            {e.reason_en && <span className="soft"> · {e.reason_en}</span>}
          </p>
        ))}
        {data.reminder && (
          <p className="editor-note">
            <span className="tag">Editor's note</span>
            Say <em>{data.reminder.correct}</em>, not <del>{data.reminder.wrong}</del>.
          </p>
        )}
      </MaherSays>
    </>
  );
}

// can't find the words (user changed them) -> whole sentence
function StillWrongLine({ data, onAsk }) {
  const { spots } = markSentence(data.sentence, (data.still_wrong || []).map((w) => ({ wrong: w })));
  const one = (text, key) => (
    <StillWrong key={key} text={text} hint={data.hint} sentence={data.sentence} onAsk={onAsk} />
  );
  if (!spots.length) return one(data.sentence, "all");
  const parts = [];
  let pos = 0;
  for (const s of spots) {
    if (s.at > pos) parts.push(data.sentence.slice(pos, s.at));
    parts.push(one(data.sentence.slice(s.at, s.end), s.at));
    pos = s.end;
  }
  parts.push(data.sentence.slice(pos));
  return parts;
}

function RetryEntry({ data, fresh, seed, onAsk }) {
  const { status } = data;
  const mood = entryMood(data);
  const line = pick(LINES[status], seed);
  const tries = data.fixing?.tries ?? 1;
  const max = data.fixing?.max_tries ?? 2;

  // done: Maher reads the right sentence, once by itself
  const right = status === "correct" ? data.sentence : data.corrected;
  const done = status !== "almost";

  return (
    <>
      {status === "skipped" ? (
        <div className="msg you">
          <div className="label">You</div>
          <p className="skipped">skipped</p>
        </div>
      ) : (
        <YouWrote hear={status === "almost" ? data.sentence : null}>
          {status === "almost" ? (
            <StillWrongLine data={data} onAsk={onAsk} />
          ) : (
            data.sentence
          )}
          {status === "correct" && <Tick />}
        </YouWrote>
      )}
      <MaherSays
        mood={mood}
        hear={done ? `${line} ${right}` : line}
        auto={done && fresh}
        action={
          status === "almost"
            ? {
                // only the wrong words, never the answer
                label: "Ask Maher for a hint →",
                onClick: () =>
                  onAsk({ sentence: data.sentence, wrong: (data.still_wrong || []).join(", ") || data.sentence, correct: "" }),
              }
            : null
        }
      >
        <p>
          {line}
          {status === "almost" && <span className="soft"> (try {tries} of {max})</span>}
        </p>
        {status === "almost" && data.hint && (
          <p className="ar-note" dir="rtl" lang="ar">
            {withBdi(data.hint)}
          </p>
        )}
        {(status === "gave_up" || status === "skipped") && <p className="answer">{data.corrected}</p>}
      </MaherSays>
    </>
  );
}

const ERRORS = {
  busy: "I'm a bit busy right now. Try again in a moment.",
  offline: "I can't hear you. Is the API running?",
};

function Entry({ entry, onAsk }) {
  const { data } = entry;
  return (
    <article className={"entry" + (entry.fresh ? " fresh" : "")}>
      {data?.kind === "check" && <CheckEntry data={data} onAsk={onAsk} />}
      {/* fixed_new looks like a normal check */}
      {data?.kind === "retry" && data.status === "fixed_new" && (
        <CheckEntry data={{ ...data, kind: "check", reply: pick(LINES.fixed_new, entry.id) }} onAsk={onAsk} />
      )}
      {data?.kind === "retry" && data.status !== "fixed_new" && (
        <RetryEntry data={data} fresh={entry.fresh} seed={entry.id} onAsk={onAsk} />
      )}
      {!data && (
        <>
          <div className="msg you">
            <div className="label">You</div>
            {entry.sentence === "skip" ? (
              <p className="skipped">skipped</p>
            ) : (
              <p className="you-text">{entry.sentence}</p>
            )}
          </div>
          {entry.loading && (
            <MaherSays>
              <p className="reading">Reading your sentence…</p>
            </MaherSays>
          )}
          {entry.error && (
            <MaherSays>
              <p className="error-note">{ERRORS[entry.error] || entry.message}</p>
            </MaherSays>
          )}
        </>
      )}
    </article>
  );
}

function Stamp({ fresh }) {
  return (
    <div className={"stamp-row" + (fresh ? " fresh" : "")}>
      <div className="seal" role="img" aria-label="Well done, أحسنت">
        <span className="seal-en">Well done</span>
        <span className="seal-ar" lang="ar">
          أحسنت
        </span>
      </div>
    </div>
  );
}

const STARTERS = ["Last weekend I", "My best friend", "Tomorrow I want to"];

export default function Chat({ entries, onAsk, onStarter }) {
  let fixed = 0;
  return (
    <>
      <MaherSays hear="Hi, I'm Maher. Write any sentence in English, about your day, your plans, anything. I'll mark it up as we go.">
        <p>
          Hi, I'm Maher. Write any sentence in English, about your day, your plans, anything. I'll mark it
          up as we go.
        </p>
        {entries.length === 0 && (
          <div className="chips" aria-label="Ideas to start">
            {STARTERS.map((s) => (
              <button key={s} className="chip" onClick={() => onStarter(s)}>
                {s} …
              </button>
            ))}
          </div>
        )}
      </MaherSays>
      {entries.map((e) => {
        // stamp after every 3rd fix
        const stamp = e.data?.status === "correct" && ++fixed % 3 === 0;
        return (
          <Fragment key={e.id}>
            <Entry entry={e} onAsk={onAsk} />
            {stamp && <Stamp fresh={e.fresh} />}
          </Fragment>
        );
      })}
    </>
  );
}
