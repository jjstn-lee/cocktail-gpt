import { createDataStreamResponse } from "ai";
import { auth } from "@/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function POST(request: Request): Promise<Response> {
  const { messages, threadId } = await request.json();
  const lastMessage = messages[messages.length - 1];

  const session = await auth();
  if (!session?.id_token) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const backendResponse = await fetch(`${API_URL}/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.id_token}`,
    },
    body: JSON.stringify({
      message: lastMessage.content,
      thread_id: threadId ?? null,
    }),
  });

  if (!backendResponse.ok) {
    const error = await backendResponse.json().catch(() => ({}));
    return new Response(
      JSON.stringify({ error: error.error || `Backend error ${backendResponse.status}` }),
      { status: backendResponse.status, headers: { "Content-Type": "application/json" } }
    );
  }

  const chatData = await backendResponse.json();

  return createDataStreamResponse({
    execute(dataStream) {
      dataStream.writeData(chatData);
      dataStream.writeMessageAnnotation({ thread_id: chatData.thread_id });
    },
  });
}
