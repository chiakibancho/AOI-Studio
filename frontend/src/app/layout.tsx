import type { Metadata } from 'next'
import './globals.css'
import QueryProvider from '@/components/providers/QueryProvider'

export const metadata: Metadata = {
  title: 'AOI Studio',
  description: '動画制作AIプラットフォーム',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body className="bg-background text-text-primary antialiased min-h-screen">
        <QueryProvider>
          {children}
        </QueryProvider>
      </body>
    </html>
  )
}
