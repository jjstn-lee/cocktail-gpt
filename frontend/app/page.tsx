"use client";

import { useEffect, useRef, useState } from "react";
import { useChat } from "ai/react";
import { useSession } from "next-auth/react";
import { submitFeedback, ChatResponse, CocktailOut } from "@/lib/api";

export default function RecommendPage() {
  const { data: session } = useSession();
  const [threadId, setThreadId] = useState<string | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { messages, input, handleInputChange, handleSubmit, isLoading, error, data, setMessages } =
    useChat({
      api: "/api/chat",
      body: { threadId },
      onFinish(message) {
        const annotation = message.annotations?.[0] as { thread_id?: string } | undefined;
        if (annotation?.thread_id) setThreadId(annotation.thread_id);
      },
    });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      setTimeout(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      }, 0);
    }
  }, [messages, isLoading]);

  const handleFeedback = async (cocktailName: string, rating: "up" | "down") => {
    if (!threadId) return;
    if (!session?.id_token) return;

    setFeedbackLoading(cocktailName);

    try {
      await submitFeedback(threadId, cocktailName, rating, session.id_token);
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    } finally {
      setFeedbackLoading(null);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setThreadId(null);
  };

  if (!session) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Please sign in to continue</h2>
        <p className="text-slate-600">
          You need to sign in with Google to access the recommendation service.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-9rem)]">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2" ref={scrollRef}>
        {messages.length === 0 && !isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-slate-500">
              <p className="text-lg">
                What are you in the mood for? Type anything to get started.
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => {
              if (msg.role === "user") {
                return (
                  <div key={msg.id} className="flex justify-end">
                    <div className="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-xs break-words">
                      {msg.content}
                    </div>
                  </div>
                );
              } else {
                // Count assistant messages up to this point to get the correct data index
                const assistantIndex = messages.slice(0, index).filter(m => m.role === "assistant").length;
                const chatData = data?.[assistantIndex] as ChatResponse | undefined;

                if (!chatData) {
                  return (
                    <div key={msg.id} className="flex justify-start">
                      <div className="bg-slate-100 rounded-lg px-4 py-3">
                        <TypingIndicator />
                      </div>
                    </div>
                  );
                }

                return (
                  <div key={msg.id} className="flex justify-start">
                    <AssistantBubble
                      chatResponse={chatData}
                      onFeedback={handleFeedback}
                      feedbackLoading={feedbackLoading}
                    />
                  </div>
                );
              }
            })}
          </>
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-lg px-4 py-3">
              <TypingIndicator />
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-2 p-3 rounded text-sm bg-red-100 text-red-900">
          {error}
        </div>
      )}

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="mt-4 flex gap-2 border-t pt-4">
        <input
          type="text"
          placeholder="Type your message..."
          value={input}
          onChange={handleInputChange}
          disabled={isLoading}
          className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500 disabled:bg-slate-100"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-400 transition"
        >
          {isLoading ? "..." : "Send"}
        </button>
        <button
          type="button"
          onClick={handleNewChat}
          className="px-6 py-2 bg-slate-400 text-white rounded-lg hover:bg-slate-500 transition"
        >
          New Chat
        </button>
      </form>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-1">
      <div className="w-2 h-2 bg-slate-400 rounded-full animate-pulse"></div>
      <div
        className="w-2 h-2 bg-slate-400 rounded-full animate-pulse"
        style={{ animationDelay: "0.2s" }}
      ></div>
      <div
        className="w-2 h-2 bg-slate-400 rounded-full animate-pulse"
        style={{ animationDelay: "0.4s" }}
      ></div>
    </div>
  );
}

function AssistantBubble({
  chatResponse,
  onFeedback,
  feedbackLoading,
}: {
  chatResponse: ChatResponse;
  onFeedback: (name: string, rating: "up" | "down") => void;
  feedbackLoading: string | null;
}) {
  return (
    <div className="bg-slate-100 rounded-lg px-4 py-3 max-w-2xl space-y-3">
      {chatResponse.degraded && (
        <div className="p-3 bg-yellow-100 text-yellow-900 rounded text-sm">
          ⚠️ Some data sources unavailable. Recommendations may be degraded.
        </div>
      )}

      {chatResponse.intent === "recommendation" && (
        <>
          <div className="bg-white p-3 rounded border border-slate-200">
            <p className="text-xs font-semibold text-slate-600">Confidence Score</p>
            <p className="text-xl font-bold text-slate-900">
              {(chatResponse.confidence_score! * 100).toFixed(0)}%
            </p>
            <p className="text-sm text-slate-700 mt-1">
              <strong>Rationale:</strong> {chatResponse.rationale}
            </p>
          </div>

          {chatResponse.recommendations && chatResponse.recommendations.length > 0 && (
            <div className="space-y-2">
              {chatResponse.recommendations.map((cocktail) => (
                <CocktailCard
                  key={cocktail.name}
                  cocktail={cocktail}
                  onThumbsUp={() => onFeedback(cocktail.name, "up")}
                  onThumbsDown={() => onFeedback(cocktail.name, "down")}
                  loading={feedbackLoading === cocktail.name}
                />
              ))}
            </div>
          )}

          {chatResponse.needs_clarification && chatResponse.clarification_question && (
            <div className="bg-blue-50 p-3 rounded border border-blue-200 text-sm">
              <p className="text-blue-900 font-semibold">
                {chatResponse.clarification_question}
              </p>
              <p className="text-blue-700 text-xs mt-1">Reply in the chat to answer.</p>
            </div>
          )}
        </>
      )}

      {chatResponse.intent === "profile_update" && (
        <div className="bg-blue-50 p-3 rounded border border-blue-200">
          <p className="text-blue-900 font-semibold">Profile Updated</p>
          <p className="text-blue-700 text-sm mt-1">{chatResponse.profile_update_summary}</p>
        </div>
      )}
    </div>
  );
}

function CocktailCard({
  cocktail,
  onThumbsUp,
  onThumbsDown,
  loading,
}: {
  cocktail: CocktailOut;
  onThumbsUp: () => void;
  onThumbsDown: () => void;
  loading: boolean;
}) {
  return (
    <div className="border border-slate-300 rounded-lg p-3 hover:shadow-lg transition bg-white">
      <h4 className="font-bold text-slate-900">{cocktail.name}</h4>

      <div className="mt-2 text-xs text-slate-600">
        <p className="font-semibold">Ingredients:</p>
        <p>{cocktail.ingredients.join(", ")}</p>
      </div>

      <div className="mt-2 text-xs text-slate-600">
        <p className="font-semibold">Method:</p>
        <p>{cocktail.method}</p>
      </div>

      <div className="mt-2 text-xs text-slate-600">
        <p className="font-semibold">Flavor Notes:</p>
        <p>{cocktail.flavor_notes.join(", ")}</p>
      </div>

      <div className="mt-2 p-2 bg-slate-50 rounded text-xs text-slate-700">
        <strong>Why:</strong> {cocktail.why_this_works}
      </div>

      <div className="mt-3 flex gap-2">
        <button
          onClick={onThumbsUp}
          disabled={loading}
          className="flex-1 px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 disabled:bg-slate-400 transition"
        >
          👍
        </button>
        <button
          onClick={onThumbsDown}
          disabled={loading}
          className="flex-1 px-2 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:bg-slate-400 transition"
        >
          👎
        </button>
      </div>
    </div>
  );
}
