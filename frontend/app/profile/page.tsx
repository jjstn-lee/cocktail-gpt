"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import {
  getProfile,
  updatePreferences,
  updateConstraints,
  UserProfileResponse,
  getSpotifyConnectUrl,
  getSpotifyStatus,
  disconnectSpotify,
  SpotifyStatusResponse,
} from "@/lib/api";

export default function ProfilePage() {
  const { data: session } = useSession();
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [prefSpirits, setPrefSpirits] = useState("");
  const [prefFlavors, setPrefFlavors] = useState("");
  const [abvPref, setAbvPref] = useState("");
  const [stylePref, setStylePref] = useState("");

  const [allergies, setAllergies] = useState("");
  const [ingredientsOnHand, setIngredientsOnHand] = useState("");
  const [maxAbv, setMaxAbv] = useState("");

  const [spotifyStatus, setSpotifyStatus] = useState<SpotifyStatusResponse | null>(null);
  const [spotifyLoading, setSpotifyLoading] = useState(false);

  const handleLoadProfile = async () => {
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const data = await getProfile(session.id_token);
      setProfile(data);

      const prefs = data.preferences || {};
      setPrefSpirits((prefs.preferred_spirits || []).join(", "));
      setPrefFlavors((prefs.preferred_flavors || []).join(", "));
      setAbvPref(prefs.abv_preference || "");
      setStylePref((prefs.style_preferences || []).join(", "));

      const constraints = data.constraints || {};
      setAllergies((constraints.allergies || []).join(", "));
      setIngredientsOnHand((constraints.ingredients_on_hand || []).join(", "));
      setMaxAbv(constraints.max_abv ? constraints.max_abv.toString() : "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSpotifyStatus = async () => {
    if (!session?.id_token) {
      return;
    }
    try {
      const status = await getSpotifyStatus(session.id_token);
      setSpotifyStatus(status);
    } catch (err) {
      // Silently fail if status check fails
      console.error("Failed to load Spotify status:", err);
    }
  };

  const handleConnectSpotify = async () => {
    console.log("[PROFILE] Connect Spotify button clicked");
    if (!session?.id_token) {
      console.log("[PROFILE] ✗ No session token");
      setError("Please sign in to continue");
      return;
    }
    console.log("[PROFILE] ✓ Session token found, fetching auth URL");
    setSpotifyLoading(true);
    try {
      const result = await getSpotifyConnectUrl(session.id_token);
      console.log("[PROFILE] ✓ Auth URL received:", result.url);
      console.log("[PROFILE] Navigating to Spotify...");
      window.location.href = result.url;
    } catch (err) {
      console.log("[PROFILE] ✗ Error getting auth URL:", err);
      setError(err instanceof Error ? err.message : "Failed to get Spotify auth URL");
      setSpotifyLoading(false);
    }
  };

  const handleDisconnectSpotify = async () => {
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }
    setSpotifyLoading(true);
    setError("");
    setSuccess("");
    try {
      await disconnectSpotify(session.id_token);
      setSuccess("Spotify disconnected successfully!");
      await handleLoadSpotifyStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect Spotify");
    } finally {
      setSpotifyLoading(false);
    }
  };

  // Load profile and Spotify status on mount
  useEffect(() => {
    if (session?.id_token) {
      handleLoadProfile();
      handleLoadSpotifyStatus();
    }
  }, [session?.id_token]);

  const handleUpdatePreferences = async () => {
    if (!profile) {
      setError("No profile loaded");
      return;
    }
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await updatePreferences(
        {
          preferred_spirits: prefSpirits ? prefSpirits.split(",").map((s) => s.trim()) : undefined,
          preferred_flavors: prefFlavors ? prefFlavors.split(",").map((f) => f.trim()) : undefined,
          abv_preference: abvPref || undefined,
          style_preferences: stylePref ? stylePref.split(",").map((s) => s.trim()) : undefined,
        },
        session.id_token
      );
      setSuccess("Preferences updated!");
      await handleLoadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update preferences");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateConstraints = async () => {
    if (!profile) {
      setError("No profile loaded");
      return;
    }
    if (!session?.id_token) {
      setError("Please sign in to continue");
      return;
    }
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      await updateConstraints(
        {
          allergies: allergies ? allergies.split(",").map((a) => a.trim()) : undefined,
          ingredients_on_hand: ingredientsOnHand ? ingredientsOnHand.split(",").map((i) => i.trim()) : undefined,
          max_abv: maxAbv ? parseFloat(maxAbv) : undefined,
        },
        session.id_token
      );
      setSuccess("Constraints updated!");
      await handleLoadProfile();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update constraints");
    } finally {
      setLoading(false);
    }
  };

  if (!session) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-bold mb-4">Please sign in to continue</h2>
        <p className="text-slate-600">You need to sign in with Google to access your profile.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4">User Profile</h2>
        <p className="text-slate-600 mb-4">Viewing profile for: <strong>{session.user?.email}</strong></p>
      </div>

      {error && (
        <div className="p-4 bg-red-100 text-red-900 rounded-lg">{error}</div>
      )}

      {success && (
        <div className="p-4 bg-green-100 text-green-900 rounded-lg">{success}</div>
      )}

      {/* Connected Accounts Section */}
      <div>
        <h3 className="text-2xl font-bold mb-4">Connected Accounts</h3>
        <div className="space-y-4 border border-slate-300 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-slate-900">Spotify</p>
              {spotifyStatus?.connected ? (
                <p className="text-sm text-green-600">
                  Connected since {new Date(spotifyStatus.connected_at || '').toLocaleDateString()}
                </p>
              ) : (
                <p className="text-sm text-slate-500">Not connected</p>
              )}
            </div>
            {spotifyStatus?.connected ? (
              <button
                onClick={handleDisconnectSpotify}
                disabled={spotifyLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-slate-400 transition"
              >
                {spotifyLoading ? "Disconnecting..." : "Disconnect"}
              </button>
            ) : (
              <button
                onClick={handleConnectSpotify}
                disabled={spotifyLoading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-slate-400 transition"
              >
                {spotifyLoading ? "Connecting..." : "Connect Spotify"}
              </button>
            )}
          </div>
        </div>
      </div>

      {profile && (
        <div className="space-y-6">
          <div>
            <h3 className="text-2xl font-bold mb-4">Preferences</h3>
            <div className="space-y-4 border border-slate-300 rounded-lg p-4">
              <FormField
                label="Preferred Spirits (comma-separated)"
                value={prefSpirits}
                onChange={setPrefSpirits}
                placeholder="e.g., vodka, gin, rum"
              />
              <FormField
                label="Preferred Flavors (comma-separated)"
                value={prefFlavors}
                onChange={setPrefFlavors}
                placeholder="e.g., citrus, herbal, sweet"
              />
              <FormField
                label="ABV Preference"
                value={abvPref}
                onChange={setAbvPref}
                placeholder="e.g., light, medium, strong"
              />
              <FormField
                label="Style Preferences (comma-separated)"
                value={stylePref}
                onChange={setStylePref}
                placeholder="e.g., cocktail, mocktail, shot"
              />
              <button
                onClick={handleUpdatePreferences}
                disabled={loading}
                className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-slate-400 transition"
              >
                {loading ? "Updating..." : "Update Preferences"}
              </button>
            </div>
          </div>

          <div>
            <h3 className="text-2xl font-bold mb-4">Constraints</h3>
            <div className="space-y-4 border border-slate-300 rounded-lg p-4">
              <FormField
                label="Allergies (comma-separated)"
                value={allergies}
                onChange={setAllergies}
                placeholder="e.g., nuts, shellfish, dairy"
              />
              <FormField
                label="Ingredients on Hand (comma-separated)"
                value={ingredientsOnHand}
                onChange={setIngredientsOnHand}
                placeholder="e.g., vodka, lime juice, soda"
              />
              <FormField
                label="Max ABV"
                value={maxAbv}
                onChange={setMaxAbv}
                placeholder="e.g., 30"
                type="number"
              />
              <button
                onClick={handleUpdateConstraints}
                disabled={loading}
                className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-slate-400 transition"
              >
                {loading ? "Updating..." : "Update Constraints"}
              </button>
            </div>
          </div>

          <div className="bg-slate-100 p-4 rounded-lg text-sm text-slate-600">
            <p>
              <strong>Last Updated:</strong> {profile.updated_at || "Never"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function FormField({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-slate-700 mb-1">
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:border-slate-500"
      />
    </div>
  );
}
