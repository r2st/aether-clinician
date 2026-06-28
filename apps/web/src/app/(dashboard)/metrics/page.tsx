'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { PerformanceMetrics, SafetyReport, ValidationRun } from '@/lib/types';
import { Button, Card } from '@/components/ui';

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Card className="text-center">
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
    </Card>
  );
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [pilot, setPilot] = useState<{ pilot_mode: boolean; message: string } | null>(null);
  const [run, setRun] = useState<ValidationRun | null>(null);
  const [reports, setReports] = useState<SafetyReport[]>([]);
  const [running, setRunning] = useState(false);

  async function refresh() {
    setMetrics(await api.performanceMetrics());
    setReports(await api.listSafetyReports());
  }

  useEffect(() => {
    void refresh();
    void api.pilotStatus().then(setPilot);
  }, []);

  async function runValidation() {
    setRunning(true);
    try {
      setRun(await api.runValidation());
      await refresh();
    } finally {
      setRunning(false);
    }
  }

  const pct = (v: number | null | undefined) =>
    v == null ? '—' : `${(v * 100).toFixed(0)}%`;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Performance & validation</h1>
        <div className="flex gap-2">
          <a href={api.samdDossierUrl('markdown')} target="_blank" rel="noreferrer">
            <Button variant="secondary">Download CDSCO dossier</Button>
          </a>
          <Button onClick={() => void runValidation()} disabled={running}>
            {running ? 'Running…' : 'Run validation harness'}
          </Button>
        </div>
      </div>

      {pilot?.pilot_mode && (
        <div className="rounded-md border border-purple-300 bg-purple-50 p-2 text-sm text-purple-900">
          Monitored pilot active — {pilot.message}
        </div>
      )}

      {metrics && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Sessions" value={metrics.total_sessions} />
            <Metric label="Hard blocks" value={metrics.hard_blocks_total} />
            <Metric label="Can't-miss flags" value={metrics.cant_miss_total} />
            <Metric label="Awaiting review" value={metrics.awaiting_review} />
            <Metric label="Verifier disagreement" value={pct(metrics.verifier_disagreement_rate)} />
            <Metric label="Degraded rate" value={pct(metrics.degraded_rate)} />
            <Metric label="Citation faithfulness" value={pct(metrics.mean_citation_faithfulness)} />
            <Metric label="Open safety reports" value={metrics.open_safety_reports} />
          </div>
          <Card>
            <p className="mb-1 text-sm font-semibold">Autonomy tier distribution</p>
            <div className="flex flex-wrap gap-3 text-sm">
              {Object.entries(metrics.autonomy_tier_distribution).map(([tier, n]) => (
                <span key={tier} className="rounded bg-slate-100 px-2 py-1">
                  {tier.replace(/_/g, ' ')}: <b>{n}</b>
                </span>
              ))}
              {Object.keys(metrics.autonomy_tier_distribution).length === 0 && (
                <span className="text-slate-400">No completed sessions yet.</span>
              )}
            </div>
          </Card>
        </>
      )}

      {run && (
        <Card>
          <p className="mb-2 text-sm font-semibold">
            Latest validation run — {run.vignette_count} vignettes
          </p>
          <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
            {Object.entries(run.metrics)
              .filter(([, v]) => typeof v === 'number')
              .map(([k, v]) => (
                <div key={k} className="rounded bg-slate-50 p-2">
                  <p className="text-xs text-slate-500">{k.replace(/_/g, ' ')}</p>
                  <p className="font-semibold">
                    {typeof v === 'number' && v <= 1 ? pct(v as number) : String(v)}
                  </p>
                </div>
              ))}
          </div>
        </Card>
      )}

      <SafetyReportForm onFiled={() => void refresh()} />

      {reports.length > 0 && (
        <Card>
          <p className="mb-2 text-sm font-semibold">Safety reports</p>
          <ul className="divide-y divide-slate-100 text-sm">
            {reports.map((r) => (
              <li key={r.id} className="flex justify-between py-1.5">
                <span>
                  <span className="font-medium">{r.severity}</span> · {r.category} — {r.description}
                </span>
                <span className="text-xs text-slate-400">{r.status}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function SafetyReportForm({ onFiled }: { onFiled: () => void }) {
  const [category, setCategory] = useState('incorrect_suggestion');
  const [severity, setSeverity] = useState('near_miss');
  const [description, setDescription] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!description.trim()) return;
    await api.fileSafetyReport({ category, severity, description });
    setDescription('');
    onFiled();
  }

  return (
    <Card>
      <p className="mb-2 text-sm font-semibold">File a safety report</p>
      <form onSubmit={submit} className="space-y-2">
        <div className="flex flex-wrap gap-2">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="incorrect_suggestion">Incorrect suggestion</option>
            <option value="missed_diagnosis">Missed diagnosis</option>
            <option value="safety_check_failure">Safety-check failure</option>
            <option value="usability">Usability</option>
            <option value="other">Other</option>
          </select>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="near_miss">Near miss</option>
            <option value="non_serious">Non-serious</option>
            <option value="serious">Serious</option>
            <option value="sentinel_event">Sentinel event</option>
          </select>
        </div>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe what happened (no patient identifiers)."
          rows={2}
          className="w-full rounded-md border border-slate-300 p-2 text-sm"
        />
        <Button type="submit" disabled={!description.trim()}>
          Submit report
        </Button>
      </form>
    </Card>
  );
}
