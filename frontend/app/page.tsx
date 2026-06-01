"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import {
  getRecommendation,
  clarify,
  submitFeedback,
  RecommendResponse,
  CocktailOut,
} from "@/lib/api";

export default function RecommendPage() {
  const { data: session } = useSession();
  const [userId, setUserId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<RecommendResponse | null>(null);
  const [clarifyAnswer, setClarifyAnswer] = useState("");
  const [feedbackLoading, setFeedbackLoading] = useState<string | null>(null);

  const handleRecommend = async () => {
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await getRecommendation(null, session.id_token);
      setResult(response);
      setClarifyAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get recommendation");
    } finally {
      setLoading(false);
    }
  };

  const handleClarify = async () => {
    if (!result || !clarifyAnswer.trim()) {
      setError("Please enter an answer to the clarification question");
      return;
    }
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await clarify(
        result.thread_id,
        clarifyAnswer,
        session.id_token
      );
      setResult(response);
      setClarifyAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clarify");
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (cocktailName: string, rating: "up" | "down") => {
    if (!result) return;
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }
    setFeedbackLoading(cocktailName);
    setError("");
    try {
      await submitFeedback(
        result.thread_id,
        cocktailName,
        rating,
        session.id_token
      );
      setError(`Feedback for "${cocktailName}" recorded!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback");
    } finally {
      setFeedbackLoading(null);
    }
  };

  if (!session) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Please sign in to continue</h2>
        <p className="text-slate-600">You need to sign in with Google to access the recommendation service.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4">Get Cocktail Recommendation</h2>
        <button
          onClick={handleRecommend}
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-400 transition"
        >
          {loading ? "Loading..." : "Get Recommendation"}
        </button>
      </div>

      {error && (
        <div className={`p-4 rounded-lg ${error.includes("recorded") ? "bg-green-100 text-green-900" : "bg-red-100 text-red-900"}`}>
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-6">
          {result.degraded && (
            <div className="p-4 bg-yellow-100 text-yellow-900 rounded-lg">
              ⚠️ Some data sources unavailable. Recommendations may be degraded.
            </div>
          )}

          <div className="bg-slate-100 p-4 rounded-lg">
            <p className="text-sm font-semibold text-slate-600">Confidence Score</p>
            <p className="text-2xl font-bold text-slate-900">
              {(result.confidence_score * 100).toFixed(0)}%
            </p>
            <p className="text-slate-700 mt-2">
              <strong>Rationale:</strong> {result.rationale}
            </p>
          </div>

          {result.recommendations.length > 0 && (
            <div>
              <h3 className="text-xl font-bold mb-4">Recommendations</h3>
              <div className="grid gap-4">
                {result.recommendations.map((cocktail) => (
                  <CocktailCard
                    key={cocktail.name}
                    cocktail={cocktail}
                    onThumbsUp={() => handleFeedback(cocktail.name, "up")}
                    onThumbsDown={() => handleFeedback(cocktail.name, "down")}
                    loading={feedbackLoading === cocktail.name}
                  />
                ))}
              </div>
            </div>
          )}

          {result.needs_clarification && (
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <p className="text-blue-900 font-semibold mb-3">
                {result.clarification_question}
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Your answer..."
                  value={clarifyAnswer}
                  onChange={(e) => setClarifyAnswer(e.target.value)}
                  className="flex-1 px-4 py-2 border border-blue-300 rounded-lg focus:outline-none focus:border-blue-500"
                  disabled={loading}
                />
                <button
                  onClick={handleClarify}
                  disabled={loading}
                  className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-400 transition"
                >
                  {loading ? "Clarifying..." : "Submit Answer"}
                </button>
              </div>
            </div>
          )}
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
    <div className="border border-slate-300 rounded-lg p-4 hover:shadow-lg transition">
      <h4 className="text-lg font-bold text-slate-900">{cocktail.name}</h4>

      <div className="mt-2 text-sm text-slate-600">
        <p className="font-semibold">Ingredients:</p>
        <p>{cocktail.ingredients.join(", ")}</p>
      </div>

      <div className="mt-2 text-sm text-slate-600">
        <p className="font-semibold">Method:</p>
        <p>{cocktail.method}</p>
      </div>

      <div className="mt-2 text-sm text-slate-600">
        <p className="font-semibold">Flavor Notes:</p>
        <p>{cocktail.flavor_notes.join(", ")}</p>
      </div>

      <div className="mt-3 p-3 bg-slate-100 rounded text-sm text-slate-700">
        <strong>Why this works:</strong> {cocktail.why_this_works}
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={onThumbsUp}
          disabled={loading}
          className="flex-1 px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-slate-400 transition"
        >
          👍 Like
        </button>
        <button
          onClick={onThumbsDown}
          disabled={loading}
          className="flex-1 px-3 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-slate-400 transition"
        >
          👎 Dislike
        </button>
      </div>
    </div>
  );
}
