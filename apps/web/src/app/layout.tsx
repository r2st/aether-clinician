import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth';
import { DemoBanner, OfflineBanner } from '@/components/Banners';

export const metadata: Metadata = {
  title: 'Aether Clinician',
  description: 'Clinician-facing diagnostic & management decision-support system',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <DemoBanner />
        <OfflineBanner />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
