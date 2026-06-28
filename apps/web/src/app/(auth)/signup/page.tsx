'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { Button, Card } from '@/components/ui';

export default function SignupPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.signup(email, password, displayName || undefined);
      await refresh();
      router.replace('/patients');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Sign up failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <form onSubmit={onSubmit} className="space-y-3">
        <h2 className="text-lg font-semibold">Create clinician account</h2>
        {error && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <input
          placeholder="Display name (optional)"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
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
          minLength={8}
          placeholder="Password (min 8 chars)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? 'Creating…' : 'Create account'}
        </Button>
        <p className="text-center text-sm text-slate-500">
          Have an account?{' '}
          <Link href="/login" className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </Card>
  );
}
