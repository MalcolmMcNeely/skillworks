export async function* readLines<T>(body: ReadableStream<Uint8Array>, signal: AbortSignal): AsyncGenerator<T> {
  const reader = body.getReader();
  const decoder = new TextDecoder();

  // Cancelled, not only left, so a waiting read ends and the API stops reading days nobody will see.
  // A body that already failed refuses to cancel, and its read throws that failure instead.
  const stop = () => void reader.cancel(signal.reason).catch(() => undefined);
  signal.addEventListener('abort', stop, { once: true });

  try {
    let unfinished = '';

    for (;;) {
      signal.throwIfAborted();
      // A body gives its next chunk only after the last, so there is nothing to wait for together.
      // oxlint-disable-next-line no-await-in-loop
      const { done, value } = await reader.read();
      signal.throwIfAborted();

      // Decoded in parts, so a character whose bytes two chunks share comes out whole.
      unfinished += done ? decoder.decode() : decoder.decode(value, { stream: true });

      const cut = done ? unfinished.length : unfinished.lastIndexOf('\n') + 1;
      const whole = unfinished.slice(0, cut);
      unfinished = unfinished.slice(cut);

      for (const [line] of whole.matchAll(/[^\n]+/g)) {
        if (line.trim() !== '') {
          yield JSON.parse(line) as T;
        }
      }

      if (done) {
        return;
      }
    }
  } finally {
    signal.removeEventListener('abort', stop);
    stop();
  }
}
