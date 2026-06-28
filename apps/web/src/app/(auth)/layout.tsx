export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-[calc(100vh-2rem)] place-items-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-center text-2xl font-bold text-slate-900">Aether Clinician</h1>
        <p className="mb-6 text-center text-sm text-slate-500">
          Diagnostic & management decision support
        </p>
        {children}
      </div>
    </main>
  );
}
