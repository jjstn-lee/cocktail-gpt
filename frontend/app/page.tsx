"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import {
  getRecommendation,
  clarify,
  submitFeedback,
  RecommendResponse,
  CocktailOut,
} from "@/lib/api";

type ChatMessage =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; response: RecommendResponse };

export default function RecommendPage() {
  const { data: session } = useSession();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [feedbackLoading, setFeedbackLoading] = useState<string | null>(null);
  const [error, setError] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      setTimeout(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      }, 0);
    }
  }, [messages, loading]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }

    // Add user message
    const userId = `user-${Date.now()}`;
    setMessages((prev) => [...prev, { id: userId, role: "user", text }]);
    setInput("");
    setLoading(true);
    setError("");

    try {
      let response: RecommendResponse;

      if (threadId === null) {
        // First message: get recommendation
        response = await getRecommendation(null, session.id_token);
        setThreadId(response.thread_id);
      } else {
        // Follow-up: clarify/refine
        response = await clarify(threadId, text, session.id_token);
      }

      // Add assistant message
      const assistantId = `assistant-${Date.now()}`;
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", response },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get response");
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (cocktailName: string, rating: "up" | "down") => {
    if (!threadId) return;
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }

    setFeedbackLoading(cocktailName);
    setError("");

    try {
      await submitFeedback(threadId, cocktailName, rating, session.id_token);
      setError(`Feedback for "${cocktailName}" recorded!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback");
    } finally {
      setFeedbackLoading(null);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setThreadId(null);
    setInput("");
    setError("");
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
        {messages.length === 0 && !loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-slate-500">
              <p className="text-lg">
                What are you in the mood for? Type anything to get started.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            if (msg.role === "user") {
              return (
                <div key={msg.id} className="flex justify-end">
                  <div className="bg-blue-600 text-white rounded-lg px-4 py-2 max-w-xs break-words">
                    {msg.text}
                  </div>
                </div>
              );
            } else {
              const response = msg.response;
              return (
                <div key={msg.id} className="flex justify-start">
                  <div className="bg-slate-100 rounded-lg px-4 py-3 max-w-2xl space-y-3">
                    {response.degraded && (
                      <div className="p-3 bg-yellow-100 text-yellow-900 rounded text-sm">
                        ⚠️ Some data sources unavailable. Recommendations may be
                        degraded.
                      </div>
                    )}

                    <div className="bg-white p-3 rounded border border-slate-200">
                      <p className="text-xs font-semibold text-slate-600">
                        Confidence Score
                      </p>
                      <p className="text-xl font-bold text-slate-900">
                        {(response.confidence_score * 100).toFixed(0)}%
                      </p>
                      <p className="text-sm text-slate-700 mt-1">
                        <strong>Rationale:</strong> {response.rationale}
                      </p>
                    </div>

                    {response.recommendations.length > 0 && (
                      <div className="space-y-2">
                        {response.recommendations.map((cocktail) => (
                          <CocktailCard
                            key={cocktail.name}
                            cocktail={cocktail}
                            onThumbsUp={() =>
                              handleFeedback(cocktail.name, "up")
                            }
                            onThumbsDown={() =>
                              handleFeedback(cocktail.name, "down")
                            }
                            loading={feedbackLoading === cocktail.name}
                          />
                        ))}
                      </div>
                    )}

                    {response.needs_clarification &&
                      response.clarification_question && (
                        <div className="bg-blue-50 p-3 rounded border border-blue-200 text-sm">
                          <p className="text-blue-900 font-semibold">
                            {response.clarification_question}
                          </p>
                          <p className="text-blue-700 text-xs mt-1">
                            Reply in the chat to answer.
                          </p>
                        </div>
                      )}
                  </div>
                </div>
              );
            }
          })
        )}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-lg px-4 py-3">
              <TypingIndicator />
            </div>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div
          className={`mt-2 p-3 rounded text-sm ${
            error.includes("recorded")
              ? "bg-green-100 text-green-900"
              : "bg-red-100 text-red-900"
          }`}
        >
          {error}
        </div>
      )}

      {/* Input bar */}
      <div className="mt-4 flex gap-2 border-t pt-4">
        <input
          type="text"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !loading) {
              e.preventDefault();
              handleSendMessage(input);
            }
          }}
          disabled={loading}
          className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500 disabled:bg-slate-100"
        />
        <button
          onClick={() => handleSendMessage(input)}
          disabled={loading || !input.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-400 transition"
        >
          {loading ? "..." : "Send"}
        </button>
        <button
          onClick={handleNewChat}
          className="px-6 py-2 bg-slate-400 text-white rounded-lg hover:bg-slate-500 transition"
        >
          New Chat
        </button>
      </div>
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
