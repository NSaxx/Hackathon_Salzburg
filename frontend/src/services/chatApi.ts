import type { MapLocation } from "../data/locations";
import { API_URL } from "./locationApi";

export interface ChatSource {
  id: string;
  name: string;
  url: string;
  provider: string;
  licence: string;
  licenceUrl: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
}

export async function sendChatMessages(
  messages: ChatMessage[],
  location: MapLocation | null,
  signal?: AbortSignal,
): Promise<ChatMessage> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: messages.map(({ role, content }) => ({ role, content })),
      location,
    }),
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `Could not get a reply (${response.status})`,
    );
  }

  const { reply, sources } = (await response.json()) as {
    reply: string;
    sources: ChatSource[];
  };
  return { role: "assistant", content: reply, sources };
}
