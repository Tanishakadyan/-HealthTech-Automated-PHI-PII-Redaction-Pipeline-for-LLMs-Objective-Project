import { Activity, AlertCircle, Loader2 } from "lucide-react";
import { useHealthCheck } from "@/lib/hooks/useHealthCheck";
import { cn } from "@/lib/utils";

export function BackendStatusPill({ className }: { className?: string }) {
  const { data, isLoading, isError } = useHealthCheck();

  const state: "online" | "offline" | "checking" = isLoading
    ? "checking"
    : isError || data?.status !== "healthy"
      ? "offline"
      : "online";

  const config = {
    online: {
      icon: Activity,
      label: "Backend online",
      classes: "bg-success/10 text-success border-success/20",
      dot: "bg-success",
    },
    offline: {
      icon: AlertCircle,
      label: "Backend unreachable",
      classes: "bg-destructive/10 text-destructive border-destructive/20",
      dot: "bg-destructive",
    },
    checking: {
      icon: Loader2,
      label: "Checking backend…",
      classes: "bg-muted text-muted-foreground border-border",
      dot: "bg-muted-foreground",
    },
  }[state];

  const Icon = config.icon;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium",
        config.classes,
        className,
      )}
      role="status"
    >
      <span className="relative flex h-2 w-2">
        {state === "online" && (
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
              config.dot,
            )}
          />
        )}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", config.dot)} />
      </span>
      {config.label}
      <Icon className={cn("h-3.5 w-3.5", state === "checking" && "animate-spin")} />
    </div>
  );
}
