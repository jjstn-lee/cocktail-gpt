import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const code = searchParams.get("code")
    const state = searchParams.get("state")
    const error = searchParams.get("error")

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

    // Build query params for backend
    const params = new URLSearchParams()
    if (code) params.append("code", code)
    if (state) params.append("state", state)
    if (error) params.append("error", error)

    const response = await fetch(`${backendUrl}/api/spotify/callback?${params}`, {
      redirect: "manual",
    })

    // Get the redirect URL from the backend response
    const redirectUrl = response.headers.get("location")

    if (redirectUrl) {
      return NextResponse.redirect(redirectUrl, { status: response.status })
    }

    // Fallback if no redirect
    return NextResponse.json(
      { error: "No redirect URL from backend" },
      { status: 500 }
    )
  } catch (error) {
    console.error("Error handling Spotify callback:", error)
    return NextResponse.redirect(
      new URL("/spotify-callback?status=error&reason=unknown", process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000")
    )
  }
}
