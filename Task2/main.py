import os

from langchain_google_genai.chat_models import (
    ChatGoogleGenerativeAIError,
    GoogleAPIError,
    GoogleRateLimitError,
)

from tutor import FAKE, build_graph


def main():
    if not FAKE and not os.getenv("GOOGLE_API_KEY"):
        print("No GOOGLE_API_KEY found. Put it in the .env file.")
        return

    graph = build_graph()
    # same thread_id every turn, so the graph keeps the state
    config = {"configurable": {"thread_id": "chat"}}

    print("Hi! I'm your English tutor. Write a sentence in English.")
    print("Type 'exit' to stop.\n")

    while True:
        try:
            sentence = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            sentence = "exit"

        if not sentence:
            continue
        if sentence.lower() == "exit":
            print("Bye! Keep practicing.")
            break

        try:
            state = graph.invoke({"sentence": sentence}, config)
        except GoogleRateLimitError:
            # 429: daily limit, stop and don't retry
            print("Daily limit reached (429). Try again tomorrow.")
            break
        except GoogleAPIError as e:
            # still failing after the retries, skip this sentence
            print(f"Server problem ({e.code}). Try again in a moment.\n")
            continue
        except ChatGoogleGenerativeAIError as e:
            # wrong key, wrong model name, ...
            print(f"Error: {e}")
            break

        print(f"\nTutor: {state['answer']}\n")


if __name__ == "__main__":
    main()
