import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
  ],
  callbacks: {
    jwt({ token, account }) {
      if (account) {
        token.id_token = account.id_token
        token.expires_at = account.expires_at
      }
      return token
    },
    session({ session, token }) {
      (session as any).id_token = token.id_token as string
      (session as any).expires_at = token.expires_at as number
      return session
    },
  },
  events: {
    async signOut() {
      // Ensure clean logout
    },
  },
  pages: {
    signIn: "/",
  },
})
