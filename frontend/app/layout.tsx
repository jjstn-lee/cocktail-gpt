import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Providers from "@/components/providers";
import { auth } from "@/auth";
import AuthButton from "@/components/auth-button";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Cocktail GPT",
  description: "AI-powered cocktail recommendations",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await auth();

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <nav className="bg-slate-900 text-white p-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-8">
              <h1 className="text-2xl font-bold">Cocktail GPT</h1>
              {session && (
                <div className="flex gap-6">
                  <a href="/" className="hover:text-slate-300 transition">
                    Recommend
                  </a>
                  <a href="/profile" className="hover:text-slate-300 transition">
                    Profile
                  </a>
                  <a href="/sessions" className="hover:text-slate-300 transition">
                    Sessions
                  </a>
                </div>
              )}
            </div>
            <AuthButton session={session} />
          </div>
        </nav>
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-8">
          <Providers>{children}</Providers>
        </main>
      </body>
    </html>
  );
}
