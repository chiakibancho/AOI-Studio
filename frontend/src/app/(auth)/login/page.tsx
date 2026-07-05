'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { setToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth'
import type { AuthResponse } from '@/types'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'

function validateEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export default function LoginPage() {
  const router = useRouter()
  const { setAuth, token } = useAuthStore()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({})
  const [apiError, setApiError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (token) {
      router.replace('/dashboard')
    }
  }, [token, router])

  function validate(): boolean {
    const newErrors: { email?: string; password?: string } = {}
    if (!email) {
      newErrors.email = 'メールアドレスを入力してください'
    } else if (!validateEmail(email)) {
      newErrors.email = '有効なメールアドレスを入力してください'
    }
    if (!password) {
      newErrors.password = 'パスワードを入力してください'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return

    setIsLoading(true)
    setApiError('')

    try {
      const res = await api.post<AuthResponse>('/api/v1/auth/login', {
        email,
        password,
      })
      const { access_token, user } = res.data
      setToken(access_token)
      setAuth(user, access_token)
      router.push('/dashboard')
    } catch (err: unknown) {
      const error = err as { response?: { status?: number } }
      if (error.response?.status === 401) {
        setApiError('メールアドレスまたはパスワードが正しくありません')
      } else {
        setApiError('ログインに失敗しました。しばらく経ってからお試しください')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      {/* Background gradient */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-accent/10 rounded-full blur-3xl" />
      </div>

      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.361a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
              </svg>
            </div>
            <span className="text-2xl font-bold text-text-primary tracking-tight">AOI Studio</span>
          </div>
          <p className="text-text-secondary text-sm">動画制作AIプラットフォーム</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl bg-surface border border-border p-8 shadow-2xl shadow-black/40">
          <h1 className="text-xl font-semibold text-text-primary mb-6">ログイン</h1>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <Input
              label="メールアドレス"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.email}
              autoComplete="email"
            />

            <Input
              label="パスワード"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
              autoComplete="current-password"
            />

            {apiError && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3">
                <p className="text-sm text-red-400">{apiError}</p>
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              isLoading={isLoading}
            >
              ログイン
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-text-secondary">
            アカウントをお持ちでない方は{' '}
            <Link
              href="/signup"
              className="text-accent hover:text-accent-hover font-medium transition-colors"
            >
              新規登録
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
