"use client"

import { signIn, signOut } from "next-auth/react"
import type { Session } from "next-auth"

export default function AuthButton({ session }: { session: Session | null }) {
  if (session) {
    return (
      <div className="flex items-center gap-4">
        <span className="text-sm">{session.user?.email}</span>
        <button
          onClick={() => signOut()}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition"
        >
          Sign Out
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={() => signIn("google")}
      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded transition"
    >
      Sign In with Google
    </button>
  )
}
