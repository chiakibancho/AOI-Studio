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

export default function SignupPage() {
  const router = useRouter()
  const { setAuth, token } = useAuthStore()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<{ name?: string; email?: string; password?: string }>({})
  const [apiError, setApiError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (token) {
      router.replace('/dashboard')
    }
  }, [token, router])

  function validate(): boolean {
    const newErrors: { name?: string; email?: string; password?: string } = {}
    if (!name.trim()) {
      newErrors.name = '名前を入力してください'
    }
    if (!email) {
      newErrors.email = 'メールアドレスを入力してください'
    } else if (!validateEmail(email)) {
      newErrors.email = '有効なメールアドレスを入力してください'
    }
    if (!password) {
      newErrors.password = 'パスワードを入力してください'
    } else if (password.length < 8) {
      newErrors.password = 'パスワードは8文字以上で入力してください'
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
      const res = await api.post<AuthResponse>('/api/v1/auth/signup', {
        name: name.trim(),
        email,
        password,
      })
      const { access_token, user } = res.data
      setToken(access_token)
      setAuth(user, access_token)
      router.push('/dashboard')
    } catch (err: unknown) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } }
      if (error.response?.status === 409) {
        setApiError('このメールアドレスは既に登録されています')
      } else {
        setApiError('登録に失敗しました。しばらく経ってからお試しください')
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
          <h1 className="text-xl font-semibold text-text-primary mb-6">新規登録</h1>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <Input
              label="名前"
              type="text"
              placeholder="山田 太郎"
              value={name}
              onChange={(e) => setName(e.target.value)}
              error={errors.name}
              autoComplete="name"
            />

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
              placeholder="8文字以上"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={errors.password}
              autoComplete="new-password"
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
              アカウントを作成
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-text-secondary">
            既にアカウントをお持ちの方は{' '}
            <Link
              href="/login"
              className="text-accent hover:text-accent-hover font-medium transition-colors"
            >
              ログイン
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
