'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Button, Card } from '@/components/ui';

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.login(email, password);
      await refresh();
      router.replace('/patients');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <form onSubmit={onSubmit} className="space-y-3">
        <h2 className="text-lg font-semibold">Sign in</h2>
        {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <input
          type="password"
          required
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>
        <p className="text-center text-sm text-slate-500">
          No account?{' '}
          <Link href="/signup" className="text-blue-600 hover:underline">
            Sign up
          </Link>
        </p>
      </form>
    </Card>
  );
}
