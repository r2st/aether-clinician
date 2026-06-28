'use client';

import { useEffect, useState } from 'react';

/** Persistent demo banner — re-appears every session (Critical Safety Rule / P1-11a). */
export function DemoBanner() {
  if (process.env.NEXT_PUBLIC_DEMO_MODE !== 'true') return null;
  return (
    <div className="bg-amber-500 px-4 py-1.5 text-center text-sm font-medium text-amber-950">
      Demo build — decision-support only, not for real patient care.
    </div>
  );
}

/** Connectivity indicator. Offline: record viewing + drug-safety checks remain available. */
export function OfflineBanner() {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  if (online) return null;
  return (
    <div className="bg-slate-700 px-4 py-1.5 text-center text-sm text-white">
      Offline Mode — patient records and drug-safety checks available. AI features paused.
    </div>
  );
}
