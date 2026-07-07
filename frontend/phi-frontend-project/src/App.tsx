import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SettingsProvider } from "@/lib/hooks/useSettings";
import { HistoryProvider } from "@/lib/hooks/useHistory";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { AppShell } from "@/components/layout/AppShell";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { Loader2 } from "lucide-react";

const LandingPage = lazy(() => import("@/features/landing/LandingPage"));
const DashboardPage = lazy(() => import("@/features/dashboard/DashboardPage"));
const RedactionPage = lazy(() => import("@/features/redaction/RedactionPage"));
const RestorePage = lazy(() => import("@/features/restore/RestorePage"));
const AnalyticsPage = lazy(() => import("@/features/analytics/AnalyticsPage"));
const HistoryPage = lazy(() => import("@/features/history/HistoryPage"));
const SettingsPage = lazy(() => import("@/features/settings/SettingsPage"));
const NotFoundPage = lazy(() => import("@/features/not-found/NotFoundPage"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function RouteFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Loader2 className="h-6 w-6 animate-spin text-primary" />
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <SettingsProvider>
          <HistoryProvider>
            <TooltipProvider delayDuration={200}>
              <BrowserRouter>
                <Suspense fallback={<RouteFallback />}>
                  <Routes>
                    <Route element={<PublicLayout />}>
                      <Route path="/" element={<LandingPage />} />
                    </Route>

                    <Route element={<AppShell />}>
                      <Route path="/dashboard" element={<DashboardPage />} />
                      <Route path="/redact" element={<RedactionPage />} />
                      <Route path="/restore" element={<RestorePage />} />
                      <Route path="/analytics" element={<AnalyticsPage />} />
                      <Route path="/history" element={<HistoryPage />} />
                      <Route path="/settings" element={<SettingsPage />} />
                    </Route>

                    <Route element={<PublicLayout />}>
                      <Route path="*" element={<NotFoundPage />} />
                    </Route>
                  </Routes>
                </Suspense>
              </BrowserRouter>
              <Toaster />
            </TooltipProvider>
          </HistoryProvider>
        </SettingsProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
