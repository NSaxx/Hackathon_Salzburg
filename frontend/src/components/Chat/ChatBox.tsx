import { Fragment, useEffect, useRef, useState } from "react";

import type { MapLocation } from "../../data/locations";
import {
  sendChatMessages,
  type ChatMessage,
  type ChatSource,
} from "../../services/chatApi";

interface Props {
  location: MapLocation | null;
}

function Sources({ sources }: { sources: ChatSource[] }) {
  const providers = [...new Map(sources.map((s) => [s.provider, s])).values()];

  return (
    <div className="sources">
      <p className="sources-label">Sources</p>
      <ul>
        {sources.map((source) => (
          <li key={source.id}>
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.name}
            </a>
          </li>
        ))}
      </ul>
      <p className="sources-credit">
        {providers.map((source, index) => (
          <Fragment key={source.provider}>
            {index > 0 && " · "}
            {source.provider},{" "}
            <a href={source.licenceUrl} target="_blank" rel="noreferrer">
              {source.licence}
            </a>
          </Fragment>
        ))}
      </p>
    </div>
  );
}

export default function ChatBox({ location }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const logRef = useRef<HTMLDivElement | null>(null);
  const replyRef = useRef<HTMLParagraphElement | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  // Scroll the log itself so the panel around it doesn't jump. A new reply starts at the
  // top of the log so it can be read downwards; anything else just needs to be in view.
  useEffect(() => {
    const log = logRef.current;
    if (!log) return;

    if (replyRef.current) {
      log.scrollTop +=
        replyRef.current.getBoundingClientRect().top - log.getBoundingClientRect().top;
    } else {
      log.scrollTop = log.scrollHeight;
    }
  }, [messages, sending, error]);

  async function send(history: ChatMessage[]) {
    const controller = new AbortController();
    abortRef.current = controller;

    setSending(true);
    setError(null);

    try {
      const reply = await sendChatMessages(history, location, controller.signal);
      setMessages([...history, reply]);
    } catch (err) {
      if (controller.signal.aborted) return;
      console.error(err);
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      if (!controller.signal.aborted) setSending(false);
    }
  }

  function submit() {
    const content = draft.trim();
    if (!content || sending) return;

    const history: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(history);
    setDraft("");
    send(history);
  }

  return (
    <section className="chat" aria-label="Chat with the concierge">
      <div className="chat-log" ref={logRef} role="log" aria-live="polite">
        {messages.length === 0 && !sending && (
          <p className="chat-hint">
            Ask about restaurants, tours, events, monuments or the weather. Select a
            place on the map to ask about it.
          </p>
        )}

        {messages.map((message, index) => (
          <Fragment key={index}>
            <p
              className={`bubble bubble--${message.role}`}
              ref={
                message.role === "assistant" && index === messages.length - 1
                  ? replyRef
                  : undefined
              }
            >
              {message.content}
            </p>
            {message.sources && message.sources.length > 0 && (
              <Sources sources={message.sources} />
            )}
          </Fragment>
        ))}

        {sending && (
          <p className="bubble bubble--assistant typing" aria-label="Typing">
            <span />
            <span />
            <span />
          </p>
        )}

        {error && (
          <div className="error-card" role="alert">
            <p>{error}</p>
            <button type="button" className="retry" onClick={() => send(messages)}>
              Try again
            </button>
          </div>
        )}
      </div>

      <form
        className="chat-form"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <textarea
          rows={1}
          value={draft}
          aria-label="Message"
          placeholder={location ? `Ask about ${location.name}…` : "Ask the concierge…"}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              submit();
            }
          }}
        />
        <button type="submit" disabled={!draft.trim() || sending} aria-label="Send">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              d="M12 19V5M5 12l7-7 7 7"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.25"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </form>
    </section>
  );
}
