import type { MapLocation } from "../data/locations";
import { API_URL } from "./locationApi";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export async function sendChatMessages(
  messages: ChatMessage[],
  location: MapLocation | null,
  signal?: AbortSignal,
): Promise<string> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, location }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Could not get a reply (${response.status})`);
  }

  const { reply } = (await response.json()) as { reply: string };
  return reply;
}
