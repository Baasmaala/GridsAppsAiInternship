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
     "reply": "Nice! Where did you go?"
   }
   ```
3. If there are mistakes, `remember` saves the new ones for this chat.
4. `reply` shows the answer and the corrections. Every 3rd sentence it
   reminds you of an old mistake.
5. Type `exit` to stop.

Only **1 model call per sentence**. The free plan gives 20 requests a day,
so that's 20 sentences.

## The graph

```
        START
          |
    check_grammar
       /      \
  mistakes   no mistakes
     |           |
  remember       |
       \        /
         reply
           |
          END   -> wait for the next sentence
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
