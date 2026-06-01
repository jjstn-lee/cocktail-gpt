"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { getSessionSummary, SessionSummary } from "@/lib/api";

export default function SessionsPage() {
  const { data: session } = useSession();
  const [sessionData, setSessionData] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLoadSessions = async () => {
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await getSessionSummary(session.id_token);
      setSessionData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load session summary");
    } finally {
      setLoading(false);
    }
  };

  // Load sessions on mount
  useEffect(() => {
    if (session?.id_token) {
      handleLoadSessions();
    }
  }, [session?.id_token]);

  if (!session) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Please sign in to continue</h2>
        <p className="text-slate-600">You need to sign in with Google to view session summaries.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4">Session Summary</h2>
        <p className="text-slate-600 mb-4">Viewing sessions for: <strong>{session.user?.email}</strong></p>
      </div>

      {error && (
        <div className="p-4 bg-red-100 text-red-900 rounded-lg">{error}</div>
      )}

      {sessionData && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm font-semibold text-blue-600">User ID</p>
              <p className="text-2xl font-bold text-blue-900">{sessionData.user_id}</p>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm font-semibold text-green-600">Session Count</p>
              <p className="text-2xl font-bold text-green-900">
                {sessionData.session_count}
              </p>
            </div>
          </div>

          <div className="bg-slate-100 border border-slate-300 rounded-lg p-4">
            <p className="text-sm font-semibold text-slate-600 mb-2">Last Run At</p>
            <p className="text-slate-900">
              {sessionData.last_run_at ? new Date(sessionData.last_run_at).toLocaleString() : "Never"}
            </p>
          </div>

          {Object.keys(sessionData.top_preferences).length > 0 && (
            <div>
              <h3 className="text-xl font-bold mb-4">Top Preferences</h3>
              <div className="bg-white border border-slate-300 rounded-lg p-4">
                <pre className="text-sm text-slate-700 overflow-auto">
                  {JSON.stringify(sessionData.top_preferences, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
