# Tutor Agent

A small English tutor that runs in the terminal, like Promova, Learna or YayTalk.
You write a sentence in English. The tutor checks your grammar, explains each
mistake **in Arabic**, and answers you like a friendly teacher.
Most tutor apps don't give explanations in Arabic.

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
   - `check_retry` asks the model if the new try is correct.
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

## Errors

- **429** (daily limit): the chat stops. No retry.
- **503** (server busy): waits 5 seconds and tries again, up to 3 times.

## Files

- `main.py`: the chat loop in the terminal
- `tutor.py`: the state, the nodes and the graph
- `tests/test_fix_step.py`: tests for the fix step and the reminder, with a fake model
  (no API key, no requests). Run: `uv run python tests/test_fix_step.py`
