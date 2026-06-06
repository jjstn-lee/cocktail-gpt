"use client"

import { signIn, signOut } from "next-auth/react"
import type { Session } from "next-auth"
import { useState } from "react"

export default function AuthButton({ session }: { session: Session | null }) {
  const [spotifyLoading, setSpotifyLoading] = useState(false)

  const handleSpotifyConnect = async () => {
    setSpotifyLoading(true)
    try {
      const idToken = (session as any)?.id_token
      if (!idToken) {
        console.error("No id_token available")
        return
      }

      const response = await fetch("/api/spotify/connect-url", {
        headers: {
          Authorization: `Bearer ${idToken}`,
        },
      })

      if (!response.ok) {
        console.error("Failed to get Spotify connect URL")
        return
      }

      const data = await response.json()
      if (data.connect_url) {
        window.location.href = data.connect_url
      }
    } catch (error) {
      console.error("Error connecting Spotify:", error)
    } finally {
      setSpotifyLoading(false)
    }
  }

  if (session) {
    // Extract first name from session
    const firstName =
      session.user?.name?.split(" ")[0] ||
      session.user?.email?.split("@")[0] ||
      "User";

    return (
      <div className="flex items-center gap-3">
        <span className="text-sm text-[#a0a0a0]">{firstName}</span>
        <button
          onClick={handleSpotifyConnect}
          disabled={spotifyLoading}
          className="px-3 py-2 text-sm font-medium text-[#f5f5f5] border border-[#2a2a2a] rounded-lg hover:bg-[#1a1a1a] hover:border-[#d97706] transition-all duration-200 disabled:opacity-50"
          title="Connect your Spotify account for personalized recommendations"
        >
          🎵 {spotifyLoading ? "..." : "Spotify"}
        </button>
        <button
          onClick={() => signOut()}
          className="px-4 py-2 text-sm font-medium text-[#f5f5f5] border border-[#2a2a2a] rounded-lg hover:bg-[#1a1a1a] hover:border-[#d97706] transition-all duration-200"
        >
          Sign Out
        </button>
      </div>
    )
  }

  return null
}
