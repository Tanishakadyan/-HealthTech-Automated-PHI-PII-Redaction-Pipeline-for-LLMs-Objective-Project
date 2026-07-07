import { Outlet, Link } from "react-router-dom";
import { ShieldCheck, Github } from "lucide-react";
import { BackendStatusPill } from "@/components/shared/BackendStatusPill";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

export function PublicLayout() {
  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-glow">
              <ShieldCheck className="h-4.5 w-4.5" />
            </span>
            <span className="text-base font-bold tracking-tight">PHI Guard</span>
          </Link>
          <div className="flex items-center gap-3">
            <BackendStatusPill className="hidden sm:inline-flex" />
            <Link
              to="/dashboard"
              className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-subtle transition-colors hover:bg-primary/90"
            >
              Open app
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>

      <footer className="border-t border-border/60 py-8">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 text-xs text-muted-foreground sm:flex-row sm:px-6 lg:px-8">
          <p>PHI Guard — reversible clinical text pseudonymization. Not a substitute for a full HIPAA compliance program.</p>
          <span className="flex items-center gap-1.5">
            <Github className="h-3.5 w-3.5" /> Built on your FastAPI backend
          </span>
        </div>
      </footer>
    </div>
  );
}
