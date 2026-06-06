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
    // If we get 401, the token may have expired. Return it so frontend can redirect to login.
    if (backendResponse.status === 401) {
      const backendError = await backendResponse.json().catch(() => ({}));
      return new Response(
        JSON.stringify({
          error: backendError.error || "Session expired. Please log in again.",
          needs_reauth: backendError.needs_reauth ?? true
        }),
        { status: 401, headers: { "Content-Type": "application/json" } }
      );
    }

    const error = await backendResponse.json().catch(() => ({}));
    return new Response(
      JSON.stringify({ error: error.error || `Backend error ${backendResponse.status}` }),
      { status: backendResponse.status, headers: { "Content-Type": "application/json" } }
    );
  }

  // Handle streaming NDJSON response
  return createDataStreamResponse({
    async execute(dataStream) {
      if (!backendResponse.body) return;

      const reader = backendResponse.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const statusMessages: string[] = [];
      let finalResponse: any = null;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");

          // Keep the last incomplete line in the buffer
          buffer = lines[lines.length - 1];

          // Process complete lines
          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i].trim();
            if (!line) continue;

            try {
              const event = JSON.parse(line);

              if (event.type === "status") {
                // Collect status updates
                console.log("[STREAM] Status:", event.message);
                statusMessages.push(event.message);
              } else if (event.type === "response") {
                // Store final response
                console.log("[STREAM] Response:", event.data);
                finalResponse = event.data;
              } else if (event.type === "error") {
                console.error("[STREAM] Backend error:", event.message);
              }
            } catch (e) {
              console.error("Failed to parse stream line:", line, e);
            }
          }
        }

        // Process any remaining data in buffer
        if (buffer.trim()) {
          try {
            const event = JSON.parse(buffer);
            if (event.type === "response") {
              finalResponse = event.data;
            }
          } catch (e) {
            console.error("Failed to parse final buffer:", buffer, e);
          }
        }

        // Send the final response with all status messages
        if (finalResponse) {
          dataStream.writeData(finalResponse);
          dataStream.writeMessageAnnotation({
            thread_id: finalResponse.thread_id,
            statuses: statusMessages,
            response: finalResponse,
          });
        }
      } finally {
        reader.releaseLock();
      }
    },
  });
}
