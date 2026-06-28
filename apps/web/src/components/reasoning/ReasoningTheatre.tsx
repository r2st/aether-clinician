'use client';

import { useEffect } from 'react';
import { Card } from '@/components/ui';
import { useReasoningStream } from '@/hooks/useReasoningStream';
import { AutonomyBadge } from './badges';
import type { AutonomyTier } from '@/lib/types';

const DOT: Record<string, string> = {
  idle: 'bg-slate-300',
  running: 'bg-blue-500 animate-pulse',
  done: 'bg-green-500',
};

/**
 * Signature screen: live agent activity during reasoning. Streams SSE events and shows each
 * agent lane activating, hypotheses appearing, can't-miss flags pulsing, the devil's-advocate
 * critique in a distinct section, and the verifier verdict last.
 */
export function ReasoningTheatre({
  sessionId,
  onComplete,
}: {
  sessionId: string;
  onComplete: () => void;
}) {
  const { state, start, stop } = useReasoningStream();

  useEffect(() => {
    start(sessionId, onComplete);
    return () => stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const ev = state.events;
  const cantMiss = (ev.cant_miss?.items as Array<{ diagnosis_name: string; why: string }>) ?? [];
  const devil = ev.devils_advocate?.critique as Record<string, unknown> | undefined;
  const verifier = ev.verifier as
    | { status?: string; autonomy_tier?: AutonomyTier; case_caveats?: string[] }
    | undefined;
  const hypotheses =
    (ev.hypotheses?.hypotheses as Array<{
      diagnosis_name: string;
      probability_band: string;
      cant_miss_flag?: boolean;
    }>) ?? [];

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Reasoning Theatre</h2>
          <span className="text-sm text-slate-500">
            {state.error
              ? 'Error'
              : state.done
                ? 'Complete'
                : state.running
                  ? 'Reasoning…'
                  : 'Connecting…'}
          </span>
        </div>
        {state.error && (
          <p className="rounded bg-red-50 p-2 text-sm text-red-700">{state.error}</p>
        )}
        <ol className="space-y-1.5">
          {state.lanes.map((lane) => (
            <li key={lane.agent} className="flex items-center gap-2 text-sm">
              <span className={`inline-block h-2.5 w-2.5 rounded-full ${DOT[lane.status]}`} />
              <span
                className={lane.status === 'done' ? 'text-slate-700' : 'font-medium text-slate-900'}
              >
                {lane.label}
              </span>
            </li>
          ))}
          {state.lanes.length === 0 && (
            <li className="text-sm text-slate-400">Waiting for the orchestrator…</li>
          )}
        </ol>
      </Card>

      {hypotheses.length > 0 && (
        <Card>
          <p className="mb-2 text-sm font-semibold text-slate-700">Hypotheses (live ranking)</p>
          <ul className="space-y-1">
            {hypotheses.map((h, i) => (
              <li key={i} className="flex items-center justify-between text-sm">
                <span>{h.diagnosis_name}</span>
                <span className="text-xs uppercase text-slate-400">{h.probability_band}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {cantMiss.length > 0 && (
        <div className="rounded-lg border border-orange-400 bg-orange-50 p-4">
          <p className="mb-1 text-sm font-bold uppercase text-orange-800">
            ● Can&apos;t-miss conditions forced onto the differential
          </p>
          <ul className="list-disc pl-5 text-sm text-orange-900">
            {cantMiss.map((c, i) => (
              <li key={i}>
                <span className="font-medium">{c.diagnosis_name}</span> — {c.why}
              </li>
            ))}
          </ul>
        </div>
      )}

      {devil && (
        <div className="rounded-lg border-l-4 border-purple-500 bg-purple-50 p-4">
          <p className="mb-1 text-sm font-bold uppercase text-purple-800">
            Devil&apos;s advocate
          </p>
          <p className="text-sm text-purple-900">{String(devil.summary ?? '')}</p>
        </div>
      )}

      {verifier && (
        <Card className="border-l-4 border-red-500">
          <div className="flex items-center justify-between">
            <p className="text-sm font-bold uppercase text-red-700">Verifier verdict</p>
            {verifier.autonomy_tier && <AutonomyBadge tier={verifier.autonomy_tier} />}
          </div>
          <p className="mt-1 text-sm text-slate-600">Status: {verifier.status}</p>
          {(verifier.case_caveats ?? []).map((c, i) => (
            <p key={i} className="mt-1 text-xs italic text-slate-500">
              • {c}
            </p>
          ))}
        </Card>
      )}
    </div>
  );
}
