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
      }
      return token
    },
    session({ session, token }) {
      session.id_token = token.id_token as string
      return session
    },
  },
})
