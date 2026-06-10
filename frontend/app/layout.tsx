import type { Metadata } from "next";
import Image from "next/image";
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
      <body className="h-screen flex flex-col bg-[#0f0f0f] text-[#f5f5f5]">
        <header className="border-b border-[#2a2a2a] backdrop-blur-sm sticky top-0 z-50 bg-[#0f0f0f]/80">
          <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3">
                <Image
                  src="/logo.png"
                  alt="Cocktail GPT"
                  width={32}
                  height={32}
                  className="rounded"
                />
                <h1 className="text-xl font-semibold tracking-tight">Cocktail-GPT</h1>
              </div>
              <div className="flex items-center gap-3">
                <a
                  href="https://justin-hisung-lee.dev/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-[#a0a0a0] hover:text-[#d97706] transition-colors duration-200"
                >
                  Portfolio
                </a>
                <span className="text-[#2a2a2a]">|</span>
                <a
                  href="https://github.com/jjstn-lee"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-medium text-[#a0a0a0] hover:text-[#d97706] transition-colors duration-200"
                >
                  GitHub
                </a>
              </div>
            </div>
            <AuthButton session={session} />
          </div>
        </header>
        <main className="flex-1 w-full overflow-hidden">
          <Providers>{children}</Providers>
        </main>
      </body>
    </html>
  );
}
