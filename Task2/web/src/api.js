async function post(url, body) {
  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return { error: "offline" };
  }
  if (res.status === 429) return { error: "limit" };
  if (res.status === 503) return { error: "busy" };
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    return { error: "other", message: data.message || `Error ${res.status}` };
  }
  return { data: await res.json() };
}

export const sendSentence = (threadId, sentence) => post("/chat", { thread_id: threadId, sentence });

// practice = Maher gives a test sentence for this mistake
export const askMaher = (threadId, question, context, practice = false) =>
  post("/ask", { thread_id: threadId, question, practice, ...(context && { context }) });
