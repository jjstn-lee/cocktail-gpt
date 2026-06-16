"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useChat } from "ai/react";
import { useSession, signIn } from "next-auth/react";
import { MarkdownText } from "@/components/MarkdownText";
import { CocktailCard } from "@/components/CocktailCard";
import { Tooltip } from "@/components/Tooltip";

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

// Flat list of loading messages that cycle every 3–7 seconds
const LOADING_MESSAGES = [
  "Replacing beer kegs",
  "Muddling mint",
  "Mixing",
  "Shaking",
  "Garnishing",
  "Straining",
  "Blending",
  "Getting yelled at",
  "Burning the ice",
  "Polishing coupe glasses",
  "Pouring",
  "Measuring",
  "Topping off",
  "Filling up",
  "Restocking bottles and cans",
  "Restocking lime juice",
  "Finding the jigger",
  "Wiping down the bar",
  "Chilling martini glass",
  "Pouring a double",
  "Taking a shot",
  "Being someone's unlicensed therapist",
  "Preparing garnishes",
  "Zesting citrus",
  "Calling for barback",
  "Rinsing the glass",
  "Pretending to remember a regular's usual",
  "Asking for ID for the 60-year-old",
  "Changing the keg mid-rush",
  "Fishing out the bottle opener",
  "Tasting for quality control",
  "Cutting more garnish",
  "Hunting for the Luxardo cherries",
  "Running the glasswasher",
  "Restocking the bitters collection",
  "Pulling from the well",
  "Double straining",
  "Doing a free pour",
  "Batching cocktails",
];

export default function ChatPage() {
  const { data: session, status } = useSession();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isScrolledToBottom, setIsScrolledToBottom] = useState(true);
  const [spotifyLoading, setSpotifyLoading] = useState(false);
  const [bartenderMessage, setBartenderMessage] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [spotifyConnected, setSpotifyConnected] = useState(false);

  const {
    messages,
    input,
    handleInputChange,
    handleSubmit: rawHandleSubmit,
    isLoading,
    error,
    setMessages,
    setInput,
  } = useChat({
    api: "/api/chat",
  });

  // Cycle through loading messages every 3–7 seconds
  useEffect(() => {
    if (!isLoading) {
      const timeoutId = setTimeout(() => setBartenderMessage(""), 300);
      return () => clearTimeout(timeoutId);
    }

    // Show a random message immediately
    const pick = () => LOADING_MESSAGES[Math.floor(Math.random() * LOADING_MESSAGES.length)];
    setBartenderMessage(pick());

    // Cycle to a new message every 3–7 seconds
    const schedule = () => {
      const delay = 3000 + Math.random() * 4000; // 3000–7000ms
      return setTimeout(() => {
        setBartenderMessage(pick());
        timerId = schedule();
      }, delay);
    };
    let timerId = schedule();

    return () => clearTimeout(timerId);
  }, [isLoading]);

  // Check Spotify connection status
  useEffect(() => {
    if (status === "authenticated" && session) {
      const checkSpotifyStatus = async () => {
        try {
          const idToken = (session as any)?.id_token;
          if (!idToken) return;

          const response = await fetch("/api/spotify/status", {
            headers: {
              Authorization: `Bearer ${idToken}`,
            },
          });

          if (response.ok) {
            const data = await response.json();
            setSpotifyConnected(data.connected || false);
          }
        } catch (error) {
          console.error("Error checking Spotify status:", error);
          setSpotifyConnected(false);
        }
      };

      checkSpotifyStatus();
    } else {
      setSpotifyConnected(false);
    }
  }, [status, session]);

  // Check token expiration and redirect if needed
  useEffect(() => {
    // Only check token expiration if user is authenticated
    if (status === "authenticated" && session && (session as any).expires_at) {
      const checkExpiration = () => {
        const expiresAt = (session as any).expires_at;
        const now = Math.floor(Date.now() / 1000);
        const bufferTime = 60; // Redirect 60 seconds before expiration

        if (now >= expiresAt - bufferTime) {
          console.log("Token expired or expiring soon, redirecting to login");
          signIn("google");
        }
      };

      // Check on mount
      checkExpiration();

      // Check every 30 seconds if token is still valid
      const interval = setInterval(checkExpiration, 30 * 1000);
      return () => clearInterval(interval);
    }
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
          <Image
            src="/logo.png"
            alt="Cocktail GPT"
            width={120}
            height={120}
            className="opacity-40 mx-auto"
          />
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
          <div className="space-y-4 flex flex-col items-center">
            <Image
              src="/logo.png"
              alt="Cocktail GPT"
              width={160}
              height={160}
            />
            <h1 className="text-4xl font-light tracking-tight">Cocktail-GPT</h1>
            <p className="text-[#a0a0a0] text-lg">Discover your next favorite cocktail</p>
          </div>

          {/* Divider */}
          <div className="h-px bg-gradient-to-r from-transparent via-[#2a2a2a] to-transparent"></div>

          {/* Auth Buttons */}
          <button
            onClick={() => signIn("google")}
            className="w-full px-6 py-3 rounded-lg border border-[#2a2a2a] bg-[#1a1a1a] hover:bg-[#252525] hover:border-[#d97706] text-[#f5f5f5] font-medium transition-all duration-200 flex items-center justify-center gap-3 hover:shadow-lg hover:shadow-[#d97706]/10"
          >
            <span className="text-xl">🔵</span>
            <span>Continue with Google</span>
          </button>

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
            <div className="text-center space-y-6 animate-in fade-in duration-500 max-w-md">
              <Image
                src="/logo.png"
                alt="Cocktail GPT"
                width={200}
                height={200}
                className="opacity-60 mx-auto"
              />
              <div className="space-y-2">
                <h2 className="text-3xl font-light tracking-tight text-[#f5f5f5]">What are you in the mood for?</h2>
                <p className="text-[#a0a0a0] text-base">I'll recommend cocktails based on your taste profile and music right now.</p>
              </div>

              <div className="flex gap-2 justify-center flex-wrap">
                {spotifyConnected ? (
                  <Tooltip content="Even though it might say connected, you might need to send your email address to the developer to be authenticated properly.">
                    <div className="px-3 py-1.5 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                      Spotify connected
                    </div>
                  </Tooltip>
                ) : (
                  <Tooltip content="Even though it says connected, you might need to send your email address to the developer to be authenticated properly.">
                    <button
                      onClick={async () => {
                        setSpotifyLoading(true);
                        try {
                          const idToken = (session as any)?.id_token;
                          if (!idToken) {
                            console.error("No id_token available");
                            return;
                          }

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
                          console.error("Error connecting to Spotify:", error);
                        } finally {
                          setSpotifyLoading(false);
                        }
                      }}
                      disabled={spotifyLoading}
                      className="px-3 py-1.5 rounded-full text-xs font-medium bg-[#2a2a2a] text-[#808080] border border-[#3a3a3a] flex items-center gap-1.5 hover:bg-[#333333] hover:border-[#d97706]/50 transition-all duration-200 disabled:opacity-50 cursor-pointer"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-[#808080]"></span>
                      {spotifyLoading ? "Connecting..." : "Connect Spotify"}
                    </button>
                  </Tooltip>
                )}
                <div className="px-3 py-1.5 rounded-full text-xs font-medium bg-[#2a2a2a] text-[#808080] border border-[#3a3a3a]">
                  More sources coming soon
                </div>
              </div>

              <div className="flex flex-col gap-2 pt-2">
                <button
                  onClick={() => {
                    setInput("Recommend me some cocktails");
                    setTimeout(() => {
                      const form = document.querySelector("form");
                      if (form) {
                        const submitBtn = form.querySelector("button[type='submit']");
                        if (submitBtn && !isLoading && "Recommend me some cocktails".trim()) {
                          form.dispatchEvent(new Event("submit", { bubbles: true }));
                        }
                      }
                    }, 0);
                  }}
                  className="px-4 py-2.5 rounded-lg border border-[#2a2a2a] bg-[#1a1a1a] text-[#f5f5f5] text-sm hover:border-[#d97706] hover:bg-[#252525] transition-all duration-200"
                >
                  Recommend me some cocktails
                </button>
                <button
                  onClick={() => {
                    setInput("What do you know about me so far?");
                    setTimeout(() => {
                      const form = document.querySelector("form");
                      if (form) {
                        const submitBtn = form.querySelector("button[type='submit']");
                        if (submitBtn && !isLoading && "What do you know about me so far?".trim()) {
                          form.dispatchEvent(new Event("submit", { bubbles: true }));
                        }
                      }
                    }, 0);
                  }}
                  className="px-4 py-2.5 rounded-lg border border-[#2a2a2a] bg-[#1a1a1a] text-[#f5f5f5] text-sm hover:border-[#d97706] hover:bg-[#252525] transition-all duration-200"
                >
                  What do you know about me so far?
                </button>
                <button
                  onClick={() => {
                    setInput("What can you do for me?");
                    setTimeout(() => {
                      const form = document.querySelector("form");
                      if (form) {
                        const submitBtn = form.querySelector("button[type='submit']");
                        if (submitBtn && !isLoading && "What can you do for me?".trim()) {
                          form.dispatchEvent(new Event("submit", { bubbles: true }));
                        }
                      }
                    }, 0);
                  }}
                  className="px-4 py-2.5 rounded-lg border border-[#2a2a2a] bg-[#1a1a1a] text-[#f5f5f5] text-sm hover:border-[#d97706] hover:bg-[#252525] transition-all duration-200"
                >
                  What can you do for me?
                </button>
              </div>
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
                <div className="space-y-4 mb-8">
                  <div className="max-w-2xl space-y-4">
                    {/* Main message */}
                    {msg.content && (
                      <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a]">
                        <MarkdownText content={msg.content} className="text-sm" />
                      </div>
                    )}

                    {/* Additional Response Content (intent-specific) */}
                    {chatData && (
                      <div className="space-y-4 mt-4">
                        {/* Recommendations */}
                        {chatData.intent === "recommendation" &&
                          chatData.recommendations &&
                          chatData.recommendations.length > 0 && (
                            <div className="space-y-3">
                              {chatData.recommendations.map(
                                (cocktail: any, idx: number) => (
                                  <CocktailCard
                                    key={cocktail.name}
                                    cocktail={cocktail}
                                    index={idx}
                                  />
                                )
                              )}
                            </div>
                          )}

                        {/* Profile Update */}
                        {chatData.intent === "profile_update" && (
                          <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a]">
                            <MarkdownText
                              content={chatData.profile_update_summary}
                              className="text-sm"
                            />
                          </div>
                        )}

                        {/* Retrieve Profile */}
                        {chatData.intent === "retrieve_profile" && chatData.profile_summary && (
                          <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a] space-y-3">
                            <MarkdownText
                              content={chatData.profile_summary}
                              className="text-sm"
                            />
                          </div>
                        )}

                        {/* Rate Cocktail */}
                        {chatData.intent === "rate_cocktail" && chatData.rating_message && (
                          <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a]">
                            <MarkdownText
                              content={chatData.rating_message}
                              className="text-sm"
                            />
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
                            <MarkdownText
                              content={chatData.explanation}
                              className="text-sm"
                            />
                          </div>
                        )}

                        {/* Conversational Fallback */}
                        {chatData.intent === "conversational_fallback" && chatData.fallback_message && (
                          <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a]">
                            <MarkdownText
                              content={chatData.fallback_message}
                              className="text-sm"
                            />
                          </div>
                        )}

                        {/* Self Information */}
                        {chatData.intent === "self_information" && chatData.self_information_message && (
                          <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a]">
                            <MarkdownText
                              content={chatData.self_information_message}
                              className="text-sm"
                            />
                          </div>
                        )}

                        {/* Manage Restrictions */}
                        {chatData.intent === "manage_restrictions" && (
                          <div className="space-y-3">
                            {chatData.restriction_summary && (
                              <div className="border border-[#2a2a2a] rounded-xl p-5 bg-[#1a1a1a]">
                                <MarkdownText
                                  content={chatData.restriction_summary}
                                  className="text-sm"
                                />
                              </div>
                            )}
                            {chatData.recommendations &&
                              chatData.recommendations.length > 0 && (
                                <div className="space-y-3">
                                  {chatData.recommendations.map(
                                    (cocktail: any, idx: number) => (
                                      <CocktailCard
                                        key={cocktail.name}
                                        cocktail={cocktail}
                                        index={idx}
                                      />
                                    )
                                  )}
                                </div>
                              )}
                          </div>
                        )}

                        {/* Rationale */}
                        {chatData.rationale && (
                          <div className="text-[#a0a0a0] text-sm italic pt-2 border-t border-[#2a2a2a]">
                            <MarkdownText content={chatData.rationale} className="text-sm" />
                          </div>
                        )}

                        {/* Confidence Score */}
                        {chatData.confidence_score !== null &&
                          chatData.confidence_score !== undefined && (
                            <div className="flex items-center gap-3 text-xs pb-4">
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
              placeholder="Describe your mood, or ask me to match your current playlist..."
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
