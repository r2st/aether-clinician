'use client';

import { useState } from 'react';
import Link from 'next/link';
import { api, ApiError } from '@/lib/api';
import type { SafetyCheckResponse } from '@/lib/types';
import { Button, Card, SafetyFlagCard } from '@/components/ui';

export default function SafetyPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [drug, setDrug] = useState('');
  const [result, setResult] = useState<SafetyCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function check(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setBusy(true);
    try {
      setResult(await api.checkDrugSafety(id, { drug_name: drug }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Check failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <Link href={`/patients/${id}`} className="text-sm text-blue-600 hover:underline">
        ← Back to patient
      </Link>
      <h1 className="text-xl font-bold">Drug safety check</h1>
      <p className="text-sm text-slate-500">
        Deterministic, offline-capable checks against this patient&apos;s allergies, current
        medications, conditions, and renal function. Hard blocks cannot be overridden.
      </p>

      <Card>
        <form onSubmit={check} className="flex gap-2">
          <input
            required
            placeholder="Proposed drug (brand or generic, e.g. Brufen)"
            value={drug}
            onChange={(e) => setDrug(e.target.value)}
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <Button type="submit" disabled={busy}>
            {busy ? 'Checking…' : 'Check'}
          </Button>
        </form>
        {error && <p className="mt-2 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
      </Card>

      {result && (
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">
              {result.proposed_drug_name}{' '}
              <span className="font-mono text-xs text-slate-400">
                ({result.proposed_drug_reference_id})
              </span>
            </h2>
            {result.is_blocked ? (
              <span className="rounded bg-red-700 px-2 py-0.5 text-xs font-bold text-white">
                BLOCKED
              </span>
            ) : (
              <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                No hard block
              </span>
            )}
          </div>

          {result.flags.length === 0 ? (
            <p className="text-sm text-slate-500">
              No interactions, contraindications, or allergy conflicts detected.
            </p>
          ) : (
            <div className="space-y-2">
              {result.flags.map((f, i) => (
                <SafetyFlagCard
                  key={i}
                  severity={f.severity}
                  isHardBlock={f.is_hard_block}
                  summary={f.summary}
                />
              ))}
            </div>
          )}

          <p className="mt-3 text-xs text-slate-400">
            Checked against {String(result.checked_against.current_medications ?? 0)} current
            medication(s), {String(result.checked_against.allergies ?? 0)} allergy(ies),{' '}
            {String(result.checked_against.conditions ?? 0)} condition(s).
            {result.checked_against.egfr_available ? ' eGFR available.' : ''}
          </p>
        </Card>
      )}
    </div>
  );
}
