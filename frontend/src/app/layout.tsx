import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { AuthProvider } from '@/contexts/AuthContext'
import { ClientProvider } from '@/contexts/ClientContext'
import { ClientMembershipProvider } from '@/contexts/ClientMembershipContext'
import { ProjectProvider } from '@/contexts/ProjectContext'
import { Toaster } from '@/components/ui/toaster'

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
})

export const metadata: Metadata = {
  title: 'PGA Application',
  description: 'PGA Application with Supabase',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning className={inter.variable}>
      <body className="font-sans antialiased">
        <ThemeProvider>
          <AuthProvider>
            <ClientProvider>
              <ClientMembershipProvider>
                <ProjectProvider>
                  {children}
                  <Toaster />
                </ProjectProvider>
              </ClientMembershipProvider>
            </ClientProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
