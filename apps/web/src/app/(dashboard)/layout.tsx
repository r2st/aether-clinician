'use client';

import Link from 'next/link';
import { useRequireAuth, useAuth } from '@/lib/auth';
import { Button } from '@/components/ui';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { account, loading } = useRequireAuth();
  const { logout } = useAuth();

  if (loading || !account) {
    return <main className="grid min-h-screen place-items-center text-slate-500">Loading…</main>;
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
        <Link href="/patients" className="text-lg font-bold text-slate-900">
          Aether Clinician
        </Link>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-500">{account.display_name ?? account.email}</span>
          <Button variant="secondary" onClick={() => logout()}>
            Sign out
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-6">{children}</main>
    </div>
  );
}
