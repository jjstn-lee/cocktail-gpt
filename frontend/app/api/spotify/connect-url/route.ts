import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get("Authorization")

    if (!authHeader) {
      return NextResponse.json(
        { error: "No authorization header" },
        { status: 401 }
      )
    }

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    const response = await fetch(`${backendUrl}/api/spotify/connect-url`, {
      headers: {
        Authorization: authHeader,
      },
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to get Spotify connect URL" },
        { status: response.status }
      )
    }

    const data = await response.json()

    // Map backend response field to frontend expectation
    return NextResponse.json({
      connect_url: data.url,
    })
  } catch (error) {
    console.error("Error getting Spotify connect URL:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
