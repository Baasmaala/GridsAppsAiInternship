# Tutor Agent

A small English tutor that runs in the terminal, like Promova, Learna or YayTalk.
You write a sentence in English. The tutor checks your grammar, explains each
mistake **in Arabic**, and answers you like a friendly teacher.
Many tutor apps don't explain mistakes in Arabic.

Built with LangGraph and Gemini (`gemini-3.5-flash`).

## What it does

1. You write a sentence in English.
2. `check_grammar` sends it to the model (with the last 4 messages of the chat).
   The model gives back JSON:
   ```json
   {
     "has_errors": true,
     "errors": [{"wrong": "I goed", "correct": "I went", "explanation_ar": "..."}],
     "corrected": "Yesterday I went to school.",
     "reply": "Nice! Where did you go?"
   }
   ```
3. If there are mistakes, `remember` saves the new ones for this chat.
4. `reply` shows the answer and the corrections. Every 3rd sentence it
   reminds you of an old mistake that is not learned yet. The one reminded
   the least comes first (then the oldest), so every mistake gets its turn.
5. **Fix step:** after a correction, the tutor asks you to write the sentence again.
   - `check_retry` asks the model if the new try is correct. It also checks
     the whole new try, so a new mistake in words you added is caught too.
     If the old ones are fixed but there is a new one, a new fix step starts.
   - Correct: the mistake is marked **learned**, no more reminders about it.
   - Wrong: `retry_reply` gives a small hint in Arabic and you try again (max 2 tries).
     After 2 wrong tries it shows the correct sentence and goes on.
   - Type `skip` to stop fixing (no model call).
   - If you make a learned mistake again, it is not learned anymore.
6. Type `exit` to stop.

Only **1 model call per message**. The free plan gives 20 requests a day,
so that's 20 messages (each try in the fix step is 1 message too).

## The graph

```
                  START
               /         \
      new sentence        fixing a mistake
           |                /         \
     check_grammar       new try      skip
        /      \            |           |
  mistakes   no mistakes  check_retry   |
     |            |           \        /
  remember        |          retry_reply
      \          /                |
         reply                   END
           |
          END     -> wait for the next message
```

## How to run

You need [uv](https://docs.astral.sh/uv/).

1. Get a Gemini API key from https://aistudio.google.com/apikey
2. Put it in a file called `.env`:
   ```
   GOOGLE_API_KEY=your-key-here
   ```
3. Run:
   ```
   uv sync
   uv run main.py
   ```

## Web site: Maher

The same tutor in the browser, with two panels:

- **Chat** (left): write anything. Wrong words are crossed out in red with the
  right words above. Hover or tap a correction to see a short reason, the
  Arabic explanation and an "Ask Maher why" button. Maher's face (the letter
  م with eyes and a red mouth) follows how you write, and his voice too.
- **Ask Maher** (right): a second agent for grammar questions. It answers in
  Arabic with short English examples, and can give a small practice question.
  "Ask Maher why" sends the mistake, the fix and the whole sentence with it.
- Under each answer, Maher suggests 2-3 next replies that fit the talk (like
  **Simpler please**, **Give me a hint**, **Show me the answer**). After a right
  answer he asks: another one, or are you done? Each button is 1 question to
  Maher, but "I'm done" needs no model call.
- **Mic**: speak instead of typing (the browser's speech to text, Chrome and
  Edge only, no model call). The audio goes to the browser's company (Google
  or Microsoft) to be turned into text. Voice may fix some mistakes by itself
  ("I goed" can come out as "I go"), so check the text before you send.
- **My mistakes**: all mistakes of this chat, learned or not. They come with
  each chat answer, so this page needs no model call. "Practice it" on a
  mistake that is not learned: Maher gives a test sentence, and if you answer
  it right, the mistake is marked learned (no more reminders about it).

Still 1 model call per chat message and 1 per question to Maher.

- `api/main.py`: a small FastAPI app.
  - `POST /chat` (`{"thread_id": "...", "sentence": "..."}`): the tutor.
  - `POST /ask` (`{"thread_id": "...", "question": "...", "context": {...}}`): Ask Maher.
  Each `thread_id` has its own memory, and the chat and Ask Maher don't share it.
- `web/`: React + Vite. It keeps the `thread_id` in the browser, "New chat" starts a new one.

Run it in two terminals (you need [Node.js](https://nodejs.org/) too):

```
# 1) the API, from Task2
uv run uvicorn api.main:app --reload

# 2) the site
cd web
npm install
npm run dev
```

Then open http://localhost:5173

### Test without API requests

Put this in `.env`:
```
FAKE_MODEL=1
```
Now `fake_model.py` answers instead of Gemini (in the site and in `main.py`).
It knows these mistakes: `goed`, `buyed`, `he go`, `she have`, `a apple`,
`he don't` and a small `i`. Ask Maher knows the same rules: "Ask Maher why",
questions about the past, "an", has/have, doesn't, and "give me a test"
(then answer it, and he checks it). Type `limit` to see the daily limit note (429).
`limit` only does this with `FAKE_MODEL=1`. Remove the line to use Gemini again.

## Errors

- **429** (daily limit): the chat stops. No retry.
- **503** (server busy): waits 5 seconds and tries again, up to 3 times.
- In the site, a 429 shows "That's all for today" and both inputs are turned
  off. A 503 shows a short note from Maher, and you can send it again.

## Known limitations

- In the fix step, the tutor only checks the sentence. If you also ask a
  question in the same message, it does not answer it.
- Mistakes are matched by their exact words, so "I goed" and "he goed"
  count as two different mistakes.
- The chat memory is lost when the program stops.
- The chat and Ask Maher use the same free quota (20 requests a day).

## Files

- `main.py`: the chat loop in the terminal
- `tutor.py`: the state, the nodes and the graph
- `ask.py`: Ask Maher, the second agent (its own graph and memory)
- `fake_model.py`: the fake model for `FAKE_MODEL=1`
- `api/main.py`: the API for the site
- `web/`: the site
- `tests/test_fix_step.py`: tests for the fix step and the reminder, with a fake model
  (no API key, no requests). Run: `uv run python tests/test_fix_step.py`
- `tests/test_api.py`: tests for the API, with `FAKE_MODEL=1`.
  Run: `uv run python tests/test_api.py`
