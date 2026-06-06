"use client";

import { useEffect, useRef, useState } from "react";
import { useChat } from "ai/react";
import { useSession, signIn } from "next-auth/react";

async function handleSpotifyLogin(idToken: string) {
  try {
    const response = await fetch("/api/spotify/connect-url", {
      headers: {
        Authorization: `Bearer ${idToken}`,
      },
    });

    if (!response.ok) {
      console.error("Failed to get Spotify connect URL");
      return;
    }

    const data = await response.json();
    if (data.connect_url) {
      window.location.href = data.connect_url;
    }
  } catch (error) {
    console.error("Error initiating Spotify login:", error);
  }
}

const BARTENDER_MESSAGES = [
  "Restocking luxardo cherries...",
  "Making 11 Long Island Iced Teas...",
  "Cleaning up the bar...",
  "Muddling fresh mint...",
  "Shaking things up...",
  "Consulting the liquor cabinet...",
  "Perfecting the pour...",
  "Selecting the finest spirits...",
  "Checking the ice machine...",
  "Appreciating the foam head...",
  "Garnishing with finesse...",
  "Reading the bar handbook...",
  "Aging this in oak...",
  "Chilling the glassware...",
  "Measuring precisely...",
  "Tasting for perfection...",
];

export default function ChatPage() {
  const { data: session, status } = useSession();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isScrolledToBottom, setIsScrolledToBottom] = useState(true);
  const [spotifyLoading, setSpotifyLoading] = useState(false);
  const [bartenderMessage, setBartenderMessage] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit: rawHandleSubmit,
    isLoading,
    error,
    setMessages,
  } = useChat({
    api: "/api/chat",
  });

  // Select a random bartender message when loading starts and change every 5-10 seconds
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    let timeoutId: NodeJS.Timeout;

    const selectNewMessage = () => {
      const message = BARTENDER_MESSAGES[Math.floor(Math.random() * BARTENDER_MESSAGES.length)];
      setBartenderMessage(message);
    };

    if (isLoading) {
      // Set initial message immediately
      selectNewMessage();

      // Change message every 5-10 seconds
      intervalId = setInterval(() => {
        selectNewMessage();
      }, Math.random() * 5000 + 5000); // 5000-10000ms
    } else {
      // Clear message when not loading
      timeoutId = setTimeout(() => setBartenderMessage(""), 300);
    }

    return () => {
      clearInterval(intervalId);
      clearTimeout(timeoutId);
    };
  }, [isLoading]);

  // Check token expiration and redirect if needed
  useEffect(() => {
    const checkAndRedirect = () => {
      if (status === "unauthenticated") {
        signIn("google");
        return;
      }

      // Check if token has expired
      if (session && (session as any).expires_at) {
        const expiresAt = (session as any).expires_at;
        const now = Math.floor(Date.now() / 1000);
        const bufferTime = 60; // Redirect 60 seconds before expiration

        if (now >= expiresAt - bufferTime) {
          console.log("Token expired or expiring soon, redirecting to login");
          signIn("google");
          return;
        }
      }
    };

    // Check on mount and whenever session changes
    checkAndRedirect();

    // Check every 30 seconds if token is still valid
    const interval = setInterval(checkAndRedirect, 30 * 1000);
    return () => clearInterval(interval);
  }, [status, session]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current && isScrolledToBottom) {
      setTimeout(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      }, 0);
    }
  }, [messages, isLoading, isScrolledToBottom]);

  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      setIsScrolledToBottom(scrollHeight - scrollTop - clientHeight < 50);
    }
  };

  const handleNewSession = () => {
    if (isLoading) return;
    setMessages([]);
    setThreadId(null);
    setInput("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    rawHandleSubmit(e, { body: { threadId } });
  };

  // Handle 401 errors during chat
  useEffect(() => {
    if (error) {
      const errorStr = typeof error === "string" ? error : String(error);
      if (
        errorStr.includes("Unauthorized") ||
        errorStr.includes("401") ||
        errorStr.includes("Session expired") ||
        errorStr.includes("needs_reauth")
      ) {
        console.error("Token error detected, redirecting to login:", errorStr);
        signIn("google");
      }
    }
  }, [error]);

  // Capture threadId from assistant message annotations
  useEffect(() => {
    if (threadId !== null) return; // already established, don't overwrite
    for (const msg of messages) {
      if (msg.role === "assistant") {
        const annotation = msg.annotations?.[0] as { thread_id?: string } | undefined;
        if (annotation?.thread_id) {
          setThreadId(annotation.thread_id);
          break;
        }
      }
    }
  }, [messages, threadId]);

  // Show loading screen while session is being checked
  if (status === "loading") {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-5xl opacity-40">🍸</div>
          <p className="text-[#808080]">Loading...</p>
        </div>
      </div>
    );
  }

  // This should not render due to useEffect redirect, but kept as safety fallback
  if (!session) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center px-4">
        <div className="w-full max-w-md space-y-8 text-center animate-in fade-in duration-500">
          {/* Logo */}
          <div className="space-y-4">
            <div className="text-6xl">🍸</div>
            <h1 className="text-4xl font-light tracking-tight">Cocktail-GPT</h1>
            <p className="text-[#a0a0a0] text-lg">Discover your next favorite cocktail</p>
          </div>

          {/* Divider */}
          <div className="h-px bg-gradient-to-r from-transparent via-[#2a2a2a] to-transparent"></div>

          {/* Auth Buttons */}
          <div className="space-y-3">
            <button
              onClick={() => signIn("google")}
              className="w-full px-6 py-3 rounded-lg border border-[#2a2a2a] bg-[#1a1a1a] hover:bg-[#252525] hover:border-[#d97706] text-[#f5f5f5] font-medium transition-all duration-200 flex items-center justify-center gap-3 hover:shadow-lg hover:shadow-[#d97706]/10"
            >
              <span className="text-xl">🔵</span>
              <span>Continue with Google</span>
            </button>

            <button
              onClick={async () => {
                setSpotifyLoading(true);
                // Sign in with Google first, then Spotify
                const result = await signIn("google", { redirect: false });
                if (result?.ok) {
                  // After Google signin, we can connect to Spotify
                  // The session will have id_token we can use
                  setTimeout(() => {
                    // Refresh session and get id_token
                    window.location.reload();
                  }, 500);
                }
                setSpotifyLoading(false);
              }}
              disabled={spotifyLoading}
              className="w-full px-6 py-3 rounded-lg border border-[#2a2a2a] bg-[#1a1a1a] hover:bg-[#252525] hover:border-[#d97706] text-[#f5f5f5] font-medium transition-all duration-200 flex items-center justify-center gap-3 hover:shadow-lg hover:shadow-[#d97706]/10 disabled:opacity-50"
            >
              <span className="text-xl">🎵</span>
              <span>{spotifyLoading ? "Connecting..." : "Connect Spotify"}</span>
            </button>
          </div>

          {/* Footer */}
          <p className="text-xs text-[#808080]">Sign in to access personalized recommendations</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#0f0f0f]">
      {/* Messages Container */}
      <div
        className="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-6 scroll-smooth flex justify-center"
        ref={scrollRef}
        onScroll={handleScroll}
      >
        <div className="w-full max-w-2xl space-y-6">
        {messages.length > 0 && (
          <div className="flex justify-end">
            <button
              onClick={handleNewSession}
              disabled={isLoading}
              className="text-xs text-[#808080] hover:text-[#d97706] border border-[#2a2a2a] hover:border-[#d97706] px-3 py-1.5 rounded-lg transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              + New Session
            </button>
          </div>
        )}

        {messages.length === 0 && !isLoading && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-4 animate-in fade-in duration-500">
              <div className="text-5xl opacity-40">🍸</div>
              <p className="text-[#808080] text-lg">What would you like to drink?</p>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => {
          const annotation = msg.annotations?.[0] as {
            response?: any;
            statuses?: string[];
            thread_id?: string;
          } | undefined;
          const chatData = annotation?.response;

          return (
            <div
              key={msg.id}
              className="animate-in fade-in slide-in-from-bottom-4 duration-300"
              style={{ animationDelay: `${idx * 50}ms` }}
            >
              {/* User Message */}
              {msg.role === "user" && (
                <div className="flex justify-end mb-4">
                  <div className="max-w-xs md:max-w-md bg-[#d97706] text-[#0f0f0f] rounded-2xl px-5 py-3 font-medium">
                    {msg.content}
                  </div>
                </div>
              )}

              {/* Assistant Message */}
              {msg.role === "assistant" && (
                <div className="space-y-4">
                  <div className="max-w-2xl space-y-4">
                    {/* Main message */}
                    <div className="text-[#f5f5f5] leading-relaxed">{msg.content}</div>

                    {/* Response Content */}
                    {chatData && (
                      <div className="space-y-4 mt-4">
                        {/* Recommendations */}
                        {chatData.intent === "recommendation" &&
                          chatData.recommendations &&
                          chatData.recommendations.length > 0 && (
                            <div className="space-y-3">
                              {chatData.recommendations.map(
                                (cocktail: any, idx: number) => (
                                  <div
                                    key={cocktail.name}
                                    className="group border border-[#2a2a2a] rounded-xl p-5 hover:border-[#d97706] hover:bg-[#1a1a1a] transition-all duration-300 cursor-pointer animate-in fade-in slide-in-from-left-4 duration-300"
                                    style={{ animationDelay: `${idx * 100}ms` }}
                                  >
                                    <div className="flex items-start justify-between gap-4 mb-3">
                                      <h3 className="text-lg font-semibold text-[#f5f5f5] group-hover:text-[#d97706] transition-colors">
                                        {cocktail.name}
                                      </h3>
                                      <span className="text-sm font-medium text-[#d97706]">
                                        #{idx + 1}
                                      </span>
                                    </div>

                                    <div className="space-y-3 text-sm">
                                      <div className="pb-2 border-b border-[#2a2a2a]">
                                        <p className="text-[#d97706] italic text-base">
                                          "{cocktail.why_this_works}"
                                        </p>
                                      </div>

                                      <div>
                                        <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
                                          Ingredients
                                        </p>
                                        <p className="text-[#a0a0a0]">
                                          {cocktail.ingredients.join(" • ")}
                                        </p>
                                      </div>

                                      <div className="h-px bg-[#2a2a2a]"></div>

                                      <div>
                                        <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
                                          Method
                                        </p>
                                        <p className="text-[#a0a0a0]">{cocktail.method}</p>
                                      </div>

                                      <div>
                                        <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
                                          Flavor Notes
                                        </p>
                                        <div className="flex gap-2 flex-wrap">
                                          {cocktail.flavor_notes.map(
                                            (note: string) => (
                                              <span
                                                key={note}
                                                className="px-3 py-1 bg-[#2a2a2a] text-[#a0a0a0] rounded-full text-xs"
                                              >
                                                {note}
                                              </span>
                                            )
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                )
                              )}
                            </div>
                          )}

                        {/* Profile Update */}
                        {chatData.intent === "profile_update" && (
                          <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a]">
                            <p className="text-[#f5f5f5] text-sm leading-relaxed">
                              {chatData.profile_update_summary}
                            </p>
                          </div>
                        )}

                        {/* Retrieve Profile */}
                        {chatData.intent === "retrieve_profile" && chatData.profile_summary && (
                          <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a] space-y-3">
                            <div className="text-[#f5f5f5] text-sm leading-relaxed whitespace-pre-wrap">
                              {chatData.profile_summary}
                            </div>
                          </div>
                        )}

                        {/* Rate Cocktail */}
                        {chatData.intent === "rate_cocktail" && chatData.rating_message && (
                          <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a]">
                            <p className="text-[#f5f5f5] text-sm leading-relaxed">
                              {chatData.rating_message}
                            </p>
                          </div>
                        )}

                        {/* Explain Recommendation */}
                        {chatData.intent === "explain_recommendation" && chatData.explanation && (
                          <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a] space-y-3">
                            {chatData.explanation_cocktail && (
                              <p className="text-[#d97706] font-semibold text-sm">
                                {chatData.explanation_cocktail}
                              </p>
                            )}
                            <p className="text-[#f5f5f5] text-sm leading-relaxed">
                              {chatData.explanation}
                            </p>
                          </div>
                        )}

                        {/* Browse by Attribute */}
                        {chatData.intent === "browse_by_attribute" &&
                          chatData.recommendations &&
                          chatData.recommendations.length > 0 && (
                            <div className="space-y-3">
                              {chatData.browse_attribute && (
                                <p className="text-[#d97706] font-semibold text-sm">
                                  {chatData.browse_attribute} cocktails
                                </p>
                              )}
                              {chatData.recommendations.map(
                                (cocktail: any, idx: number) => (
                                  <div
                                    key={cocktail.name}
                                    className="group border border-[#2a2a2a] rounded-xl p-5 hover:border-[#d97706] hover:bg-[#1a1a1a] transition-all duration-300 cursor-pointer animate-in fade-in slide-in-from-left-4 duration-300"
                                    style={{ animationDelay: `${idx * 100}ms` }}
                                  >
                                    <div className="flex items-start justify-between gap-4 mb-3">
                                      <h3 className="text-lg font-semibold text-[#f5f5f5] group-hover:text-[#d97706] transition-colors">
                                        {cocktail.name}
                                      </h3>
                                      <span className="text-sm font-medium text-[#d97706]">
                                        #{idx + 1}
                                      </span>
                                    </div>

                                    <div className="space-y-3 text-sm">
                                      <div className="pb-2 border-b border-[#2a2a2a]">
                                        <p className="text-[#d97706] italic text-base">
                                          "{cocktail.why_this_works}"
                                        </p>
                                      </div>

                                      <div>
                                        <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
                                          Ingredients
                                        </p>
                                        <p className="text-[#a0a0a0]">
                                          {cocktail.ingredients.join(" • ")}
                                        </p>
                                      </div>

                                      <div className="h-px bg-[#2a2a2a]"></div>

                                      <div>
                                        <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
                                          Method
                                        </p>
                                        <p className="text-[#a0a0a0]">{cocktail.method}</p>
                                      </div>

                                      <div>
                                        <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
                                          Flavor Notes
                                        </p>
                                        <div className="flex gap-2 flex-wrap">
                                          {cocktail.flavor_notes.map(
                                            (note: string) => (
                                              <span
                                                key={note}
                                                className="px-3 py-1 bg-[#2a2a2a] text-[#a0a0a0] rounded-full text-xs"
                                              >
                                                {note}
                                              </span>
                                            )
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                )
                              )}
                            </div>
                          )}

                        {/* Manage Restrictions */}
                        {chatData.intent === "manage_restrictions" && (
                          <div className="space-y-3">
                            {chatData.restriction_summary && (
                              <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a]">
                                <p className="text-[#f5f5f5] text-sm leading-relaxed">
                                  {chatData.restriction_summary}
                                </p>
                              </div>
                            )}
                            {chatData.recommendations &&
                              chatData.recommendations.length > 0 && (
                                <div className="space-y-3">
                                  {chatData.recommendations.map(
                                    (cocktail: any, idx: number) => (
                                      <div
                                        key={cocktail.name}
                                        className="group border border-[#2a2a2a] rounded-xl p-5 hover:border-[#d97706] hover:bg-[#1a1a1a] transition-all duration-300 cursor-pointer animate-in fade-in slide-in-from-left-4 duration-300"
                                        style={{ animationDelay: `${idx * 100}ms` }}
                                      >
                                        <div className="flex items-start justify-between gap-4 mb-3">
                                          <h3 className="text-lg font-semibold text-[#f5f5f5] group-hover:text-[#d97706] transition-colors">
                                            {cocktail.name}
                                          </h3>
                                          <span className="text-sm font-medium text-[#d97706]">
                                            #{idx + 1}
                                          </span>
                                        </div>

                                        <div className="space-y-3 text-sm">
                                          <div>
                                            <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
                                              Ingredients
                                            </p>
                                            <p className="text-[#a0a0a0]">
                                              {cocktail.ingredients.join(" • ")}
                                            </p>
                                          </div>

                                          <div className="h-px bg-[#2a2a2a]"></div>

                                          <div>
                                            <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
                                              Method
                                            </p>
                                            <p className="text-[#a0a0a0]">{cocktail.method}</p>
                                          </div>

                                          <div>
                                            <p className="text-[#808080] text-xs uppercase tracking-wide mb-1">
                                              Flavor Notes
                                            </p>
                                            <div className="flex gap-2 flex-wrap">
                                              {cocktail.flavor_notes.map(
                                                (note: string) => (
                                                  <span
                                                    key={note}
                                                    className="px-3 py-1 bg-[#2a2a2a] text-[#a0a0a0] rounded-full text-xs"
                                                  >
                                                    {note}
                                                  </span>
                                                )
                                              )}
                                            </div>
                                          </div>

                                          <div className="pt-2 border-t border-[#2a2a2a]">
                                            <p className="text-[#d97706] italic text-xs">
                                              "{cocktail.why_this_works}"
                                            </p>
                                          </div>
                                        </div>
                                      </div>
                                    )
                                  )}
                                </div>
                              )}
                          </div>
                        )}

                        {/* Clarification */}
                        {chatData.needs_clarification &&
                          chatData.clarification_question && (
                            <div className="border-l-2 border-[#d97706] bg-[#1a1a1a] rounded-lg px-5 py-4 space-y-2">
                              <p className="text-[#d97706] font-semibold text-sm">
                                Help me understand better
                              </p>
                              <p className="text-[#f5f5f5] text-sm">
                                {chatData.clarification_question}
                              </p>
                            </div>
                          )}

                        {/* Rationale */}
                        {chatData.rationale && (
                          <div className="text-[#a0a0a0] text-sm leading-relaxed italic pt-2 border-t border-[#2a2a2a]">
                            {chatData.rationale}
                          </div>
                        )}

                        {/* Confidence Score */}
                        {chatData.confidence_score !== null &&
                          chatData.confidence_score !== undefined && (
                            <div className="flex items-center gap-3 text-xs">
                              <div className="flex-1 h-1 bg-[#2a2a2a] rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-gradient-to-r from-[#d97706] to-[#b45309] transition-all duration-500"
                                  style={{
                                    width: `${chatData.confidence_score * 100}%`,
                                  }}
                                ></div>
                              </div>
                              <span className="text-[#808080]">
                                {(chatData.confidence_score * 100).toFixed(0)}%
                              </span>
                            </div>
                          )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {isLoading && (
          <div className="animate-in fade-in duration-300">
            <div className="flex items-center gap-3">
              <p className="text-[#a0a0a0] italic text-sm">{bartenderMessage}</p>
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-[#d97706] animate-bounce" style={{ animationDelay: "0ms" }}></div>
                <div className="w-2 h-2 rounded-full bg-[#d97706] animate-bounce" style={{ animationDelay: "150ms" }}></div>
                <div className="w-2 h-2 rounded-full bg-[#d97706] animate-bounce" style={{ animationDelay: "300ms" }}></div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="animate-in fade-in duration-300">
            <div className="border border-red-500/30 bg-red-500/10 text-red-400 rounded-lg px-4 py-3 text-sm max-w-md">
              {typeof error === "string" && (error as string).includes("Unauthorized")
                ? "Your session has expired. Redirecting to login..."
                : typeof error === "string"
                  ? (error as string)
                  : String(error)}
            </div>
          </div>
        )}
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-[#2a2a2a] bg-[#0f0f0f] px-4 md:px-6 py-4 flex justify-center">
        <form onSubmit={handleSubmit} className="w-full max-w-2xl flex gap-3">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="Ask for recommendations, describe your mood..."
              value={input}
              onChange={handleInputChange}
              disabled={isLoading}
              className="w-full px-5 py-3 rounded-xl border border-[#2a2a2a] bg-[#1a1a1a] text-[#f5f5f5] placeholder-[#808080] focus:outline-none focus:border-[#d97706] focus:ring-1 focus:ring-[#d97706]/20 transition-all duration-200 disabled:opacity-50"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 rounded-xl bg-[#d97706] text-[#0f0f0f] font-semibold hover:bg-[#b45309] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:shadow-lg hover:shadow-[#d97706]/20"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
