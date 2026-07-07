import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

export function AppShell() {
  return (
    <div className="flex min-h-dvh bg-background">
      <aside className="hidden w-64 shrink-0 lg:block">
        <div className="fixed h-dvh w-64">
          <Sidebar />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-7xl">
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </div>
  );
}
