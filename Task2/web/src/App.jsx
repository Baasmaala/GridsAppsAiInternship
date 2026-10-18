import { useEffect, useRef, useState } from "react";
import AskPanel, { SUGGESTIONS } from "./AskPanel.jsx";
import Chat, { entryMood } from "./Chat.jsx";
import Face from "./Face.jsx";
import Mic from "./Mic.jsx";
import Mistakes from "./Mistakes.jsx";
import { askMaher, sendSentence } from "./api.js";

const SAVE_KEY = "maher-page";
const ASK_OPEN_KEY = "maher-ask-open";

// open or closed Ask panel, only for this browser
function loadAskOpen() {
  try {
    return localStorage.getItem(ASK_OPEN_KEY) !== "0";
  } catch {
    return true;
  }
}

const newPage = () => ({ threadId: crypto.randomUUID(), entries: [], fixing: null, mistakes: [], ask: [] });

// localStorage can throw (private window), so always try/catch
function loadPage() {
  try {
    const page = JSON.parse(localStorage.getItem(SAVE_KEY));
    if (page?.threadId) return { ...newPage(), ...page };
  } catch {}
  return newPage();
}

function savePage(page) {
  // don't save half done messages, and no animation after a reload
  const done = (list) => list.filter((m) => m.data || m.role === "you").map(({ fresh, ...m }) => m);
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify({ ...page, entries: done(page.entries), ask: done(page.ask) }));
  } catch {}
}

const today = new Date().toLocaleDateString("en-GB", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
});

const MOOD_TEXT = {
  start: ["Ready when you are.", "Maher's face follows your writing."],
  reading: ["Reading your sentence…", "One moment."],
  neutral: ["Let's keep going.", "Write your next sentence."],
  smiling: ["Lovely, that's correct.", "Keep going, write another one."],
  sad: ["Hmm, a small slip.", "Maher's face follows your writing. Fix the mistake to cheer him up."],
  veryHappy: ["Fixed it. Nice work!", "That one is learned now."],
  disappointed: ["Skipped this one.", "No problem, the next one is yours."],
  limit: ["That's all for today.", "You used today's practice. Maher will be back tomorrow."],
};

// "I'm done": Maher says bye on the page, no model call
const DONE = /\b(i'?m done|i am done|done,? thanks|no,? thanks|that'?s all|finished)\b/i;
const BYE = {
  answer_ar: "عمل رائع اليوم! اسألني عن أي شيء في الإنجليزية، في أي وقت.",
  examples: [],
  practice: "",
  passed: false,
  suggestions: SUGGESTIONS,
};

// keep a scroll box at the bottom while it grows, until the user scrolls up
function useStickToBottom(dep) {
  const ref = useRef(null);
  const stick = useRef(true);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let lastTop = el.scrollTop;
    const onScroll = () => {
      const gap = el.scrollHeight - el.clientHeight - el.scrollTop;
      if (gap < 60) stick.current = true;
      else if (el.scrollTop < lastTop) stick.current = false;
      lastTop = el.scrollTop;
    };
    const ro = new ResizeObserver(() => stick.current && (el.scrollTop = el.scrollHeight));
    [...el.children].forEach((c) => ro.observe(c));
    el.addEventListener("scroll", onScroll, { passive: true });
    el.scrollTop = el.scrollHeight;
    return () => {
      ro.disconnect();
      el.removeEventListener("scroll", onScroll);
    };
  }, [dep]);
  return { ref, stick };
}

function usePhone() {
  const query = "(max-width: 860px)";
  const [phone, setPhone] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setPhone(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return phone;
}

export default function App() {
  const [page, setPage] = useState(loadPage);
  const [text, setText] = useState("");
  const [voiceUsed, setVoiceUsed] = useState(false); // the text came from the mic
  const [micError, setMicError] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [asking, setAsking] = useState(false);
  const [limit, setLimit] = useState(false);
  const [view, setView] = useState("chat"); // chat, mistakes, ask (ask = phone only)
  const phone = usePhone();
  // Ask panel on big screens: open, closed, or peeking
  const [askOpen, setAskOpen] = useState(loadAskOpen);
  const [peek, setPeek] = useState(false);
  const [unread, setUnread] = useState(false);
  const peekTimer = useRef(null);
  const closedAt = useRef(0);
  const askRef = useRef(null);
  const askSeen = useRef(true); // can the user see the panel right now
  askSeen.current = phone ? view === "ask" : askOpen || peek;
  const inputRef = useRef(null);
  const askInputRef = useRef(null);
  const { threadId, entries, fixing, mistakes, ask } = page;

  // no "ask" view on big screens
  const shown = !phone && view === "ask" ? "chat" : view;

  const chatBox = useStickToBottom(`${shown}-${phone}`);
  const askBox = useStickToBottom(`${shown}-${phone}`);

  useEffect(() => savePage(page), [page]);

  useEffect(() => {
    try {
      localStorage.setItem(ASK_OPEN_KEY, askOpen ? "1" : "0");
    } catch {}
  }, [askOpen]);

  useEffect(() => {
    // Esc or a click outside closes the peek
    if (!peek) return;
    const onKey = (ev) => ev.key === "Escape" && setPeek(false);
    const onDown = (ev) => !askRef.current?.contains(ev.target) && !ev.target.closest?.(".ask-tab") && setPeek(false);
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [peek]);

  function openAsk() {
    clearTimeout(peekTimer.current);
    setAskOpen(true);
    setPeek(false);
    setUnread(false);
  }

  function closeAsk() {
    // the tab appears under the mouse, don't peek again right away
    closedAt.current = Date.now();
    setAskOpen(false);
    setPeek(false);
  }

  function startPeek() {
    clearTimeout(peekTimer.current);
    if (!askOpen && Date.now() - closedAt.current > 700) {
      setPeek(true);
      setUnread(false);
    }
  }

  function endPeek() {
    // not while the user is typing in the panel
    clearTimeout(peekTimer.current);
    peekTimer.current = setTimeout(() => {
      if (!askRef.current?.contains(document.activeElement)) setPeek(false);
    }, 300);
  }

  async function send(sentence) {
    if (!sentence || waiting || limit) return;
    const id = crypto.randomUUID();
    setWaiting(true);
    setText("");
    setVoiceUsed(false);
    chatBox.stick.current = true;
    setPage((p) => ({ ...p, entries: [...p.entries, { id, sentence, loading: true }] }));

    const res = await sendSentence(threadId, sentence);
    setWaiting(false);

    if (res.error === "limit") {
      // the mood card says it, so drop this entry
      setLimit(true);
      setPage((p) => ({ ...p, entries: p.entries.filter((e) => e.id !== id) }));
      return;
    }
    setPage((p) => ({
      ...p,
      fixing: res.data ? res.data.fixing : p.fixing,
      mistakes: res.data ? res.data.mistakes : p.mistakes,
      entries: p.entries.map((e) =>
        e.id === id ? { id, sentence, fresh: true, data: res.data, error: res.error, message: res.message } : e
      ),
    }));
    // 503 etc: put the sentence back
    if (res.error && sentence !== "skip") setText(sentence);
    inputRef.current?.focus();
  }

  // context = a chat mistake or null, practice = Practice it
  async function sendAsk(context, question, practice = false) {
    if (asking || limit) return;
    // no correct word = still fixing, ask for help only
    const q =
      question ||
      (practice
        ? `Give me a test for "${context.wrong}".`
        : context.correct
          ? `Why is it "${context.correct}" and not "${context.wrong}"?`
          : `Can you help me fix "${context.wrong}"?`);
    const you = { id: crypto.randomUUID(), role: "you", text: q, context, practice };
    const id = crypto.randomUUID();
    if (!context && DONE.test(q)) {
      setPage((p) => ({ ...p, ask: [...p.ask, you, { id, role: "maher", data: BYE }] }));
      return;
    }
    // anything that leads to Maher opens his panel
    if (phone) setView("ask");
    else openAsk();
    setAsking(true);
    askBox.stick.current = true;
    setPage((p) => ({ ...p, ask: [...p.ask, you, { id, role: "maher", loading: true }] }));

    const res = await askMaher(threadId, q, context, practice);
    setAsking(false);
    if (!askSeen.current) setUnread(true);
    if (res.error === "limit") setLimit(true);
    setPage((p) => ({
      ...p,
      // passed: learned now
      mistakes: res.data?.learned ? res.data.mistakes : p.mistakes,
      ask: p.ask.map((m) =>
        m.id === id ? { id, role: "maher", data: res.data, error: res.error, message: res.message } : m
      ),
    }));
  }

  function pickStarter(start) {
    setText(start + " ");
    // cursor to the end
    requestAnimationFrame(() => {
      const el = inputRef.current;
      el?.focus();
      el?.setSelectionRange(el.value.length, el.value.length);
    });
  }

  function newChat() {
    setPage(newPage());
    setLimit(false);
    setText("");
    setView("chat");
  }

  // Maher's face follows the last thing that happened
  const last = entries[entries.length - 1];
  let moodKey = "start";
  if (limit) moodKey = "limit";
  else if (waiting) moodKey = "reading";
  else if (last?.data) moodKey = entryMood(last.data);
  else if (last) moodKey = "neutral";
  const face = { start: "neutral", reading: "neutral", limit: "disappointed" }[moodKey] || moodKey;
  const [title, sub] = MOOD_TEXT[moodKey];

  const tabs = phone
    ? [["chat", "Chat"], ["ask", "Ask Maher"], ["mistakes", "My mistakes"]]
    : [["chat", "Chat"], ["mistakes", "My mistakes"]];

  return (
    <div className="app">
      <div className="topbar">
        <span className="date">{today}</span>
        <nav aria-label="Pages">
          {tabs.map(([v, name]) => (
            <button
              key={v}
              className={shown === v ? "on" : ""}
              onClick={() => setView(v)}
              aria-current={shown === v ? "page" : undefined}
            >
              {name}
              {v === "mistakes" && mistakes.length > 0 && <span className="count">{mistakes.length}</span>}
            </button>
          ))}
          <button onClick={newChat} disabled={waiting || asking}>
            New chat
          </button>
        </nav>
      </div>

      <header className="masthead">
        <Face mood="smiling" size={phone ? 44 : 62} label={false} plain />
        <h1>Maher</h1>
        <p className="tagline">
          Chat about anything. Your writing gets marked up as you go, and Maher explains every mistake.
        </p>
      </header>

      <div
        className={
          "panels show-" + shown + (phone ? "" : askOpen ? " ask-open" : " ask-closed" + (peek ? " ask-peek" : ""))
        }
      >
        <section className="left" aria-label={shown === "mistakes" ? "My mistakes" : "Chat"}>
          {shown === "mistakes" ? (
            <div className="chat-scroll">
              <Mistakes mistakes={mistakes} onAsk={(c) => sendAsk(c)} onPractice={(c) => sendAsk(c, null, true)} />
            </div>
          ) : (
            <>
              <div className="chat-scroll" ref={chatBox.ref}>
                <div className="mood" role="status">
                  <Face mood={face} size={phone ? 46 : 58} />
                  <div>
                    <p className="mood-title">{title}</p>
                    <p className="mood-sub">{sub}</p>
                  </div>
                </div>
                <div className="thread">
                  <Chat entries={entries} onAsk={sendAsk} onStarter={pickStarter} />
                </div>
              </div>

              <footer className="composer">
                <p className="composer-label">
                  {limit
                    ? "Daily limit reached · back tomorrow"
                    : fixing
                      ? `Rewrite your sentence · try ${fixing.tries + 1} of ${fixing.max_tries}`
                      : "Write a sentence"}
                </p>
                <form
                  className="composer-row"
                  onSubmit={(ev) => {
                    ev.preventDefault();
                    send(text.trim());
                  }}
                >
                  <input
                    ref={inputRef}
                    value={text}
                    onChange={(ev) => setText(ev.target.value)}
                    placeholder={
                      limit ? "See you tomorrow" : fixing ? "Write or say it again, corrected…" : "Write or say anything in English…"
                    }
                    maxLength={500}
                    disabled={limit}
                    autoFocus={!phone}
                    aria-label="Your sentence"
                    autoComplete="off"
                    spellCheck={false}
                  />
                  <Mic
                    lang="en-US"
                    value={text}
                    disabled={waiting || limit}
                    onText={(t) => {
                      setText(t);
                      setVoiceUsed(true);
                    }}
                    onError={setMicError}
                  />
                  <button className="send" disabled={waiting || limit || !text.trim()}>
                    Send
                  </button>
                  {fixing && !limit && (
                    <button type="button" className="skip" onClick={() => send("skip")} disabled={waiting}>
                      Skip
                    </button>
                  )}
                </form>
                {micError ? (
                  <p className="composer-hint error-note">{micError}</p>
                ) : voiceUsed && text ? (
                  <p className="composer-hint voice-note">
                    Voice may fix some mistakes for you. Check the text before you send.
                  </p>
                ) : (
                  <p className="composer-hint">Tap a red word, or press Ask Maher, to talk about it.</p>
                )}
              </footer>
            </>
          )}
        </section>

        {!phone && !askOpen && (
          <button
            className="ask-tab"
            onClick={openAsk}
            onMouseEnter={startPeek}
            onMouseLeave={endPeek}
            aria-label={unread ? "Open Ask Maher, new answer" : "Open Ask Maher"}
          >
            <Face mood="neutral" size={28} label={false} />
            <span>Ask Maher</span>
            {unread && <i className="dot" />}
          </button>
        )}

        <aside
          className="right"
          aria-label="Ask Maher"
          ref={askRef}
          inert={!phone && !askOpen && !peek}
          onMouseEnter={() => peek && clearTimeout(peekTimer.current)}
          onMouseLeave={() => peek && endPeek()}
        >
          <AskPanel
            onClose={phone ? null : askOpen ? closeAsk : openAsk}
            pinned={askOpen}
            messages={ask}
            onAsk={sendAsk}
            waiting={asking}
            limit={limit}
            inputRef={askInputRef}
            scrollRef={askBox.ref}
          />
        </aside>
      </div>
    </div>
  );
}
