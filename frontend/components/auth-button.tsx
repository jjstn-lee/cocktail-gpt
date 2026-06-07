"use client"

import { signOut } from "next-auth/react"
import type { Session } from "next-auth"
import { useState } from "react"

export default function AuthButton({ session }: { session: Session | null }) {
  const [signOutLoading, setSignOutLoading] = useState(false)

  const handleSignOut = async () => {
    setSignOutLoading(true)
    try {
      const idToken = (session as any)?.id_token
      if (idToken) {
        await fetch("/api/spotify/disconnect", {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${idToken}`,
          },
        }).catch((error) => {
          console.error("Error disconnecting Spotify:", error)
        })
      }
    } finally {
      await signOut()
    }
  }

  if (session) {
    // Extract first name from session
    const firstName =
      session.user?.name?.split(" ")[0] ||
      session.user?.email?.split("@")[0] ||
      "User";

    // Get initials for avatar
    const getInitials = () => {
      const name = session.user?.name || "U";
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2);
    };

    return (
      <div className="flex items-center gap-2">
        <a
          href="https://justin-hisung-lee.dev/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-3 py-2 rounded-full border border-[#2a2a2a] hover:border-[#d97706] bg-[#1a1a1a] hover:bg-[#252525] transition-all duration-200 group"
        >
          <div className="w-6 h-6 rounded-full bg-[#d97706] flex items-center justify-center text-xs font-semibold text-[#0f0f0f] group-hover:shadow-lg group-hover:shadow-[#d97706]/20 leading-none">
            {getInitials()}
          </div>
          <span className="text-sm font-medium text-[#a0a0a0] group-hover:text-[#d97706] leading-none">
            {firstName}
          </span>
          <span className="text-sm text-[#d97706] font-semibold leading-none">Portfolio</span>
        </a>

        <a
          href="https://github.com/jjstn-lee"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#2a2a2a] hover:border-[#d97706] bg-[#1a1a1a] hover:bg-[#252525] transition-all duration-200"
        >
          <span className="text-sm">🔗</span>
          <span className="text-sm font-medium text-[#a0a0a0] hover:text-[#d97706]">
            GitHub
          </span>
        </a>

        <button
          onClick={handleSignOut}
          disabled={signOutLoading}
          className="px-4 py-2 text-sm font-medium text-[#f5f5f5] border border-[#2a2a2a] rounded-lg hover:bg-[#1a1a1a] hover:border-[#d97706] transition-all duration-200 disabled:opacity-50"
        >
          {signOutLoading ? "Signing out..." : "Sign Out"}
        </button>
      </div>
    )
  }

  return null
}
