import { NavLink } from "react-router-dom";
import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/components/layout/nav-items";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col gap-6 border-r border-border/70 bg-card/60 px-4 py-6">
      <NavLink to="/" className="flex items-center gap-2 px-2" onClick={onNavigate}>
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-glow">
          <ShieldCheck className="h-4.5 w-4.5" />
        </span>
        <span className="text-base font-bold tracking-tight text-foreground">
          PHI Guard
        </span>
      </NavLink>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "group flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted/70 hover:text-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                <span className="flex items-center gap-3">
                  <item.icon
                    className={cn(
                      "h-4.5 w-4.5",
                      isActive ? "text-primary" : "text-muted-foreground/80 group-hover:text-foreground",
                    )}
                  />
                  {item.label}
                </span>
                {item.shortcut && (
                  <kbd className="hidden rounded border border-border bg-muted px-1.5 py-0.5 font-data text-[10px] text-muted-foreground lg:inline-block">
                    {item.shortcut}
                  </kbd>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="rounded-lg border border-border/70 bg-muted/40 px-3 py-3 text-xs text-muted-foreground">
        <p className="font-semibold text-foreground/80">De-identification only</p>
        <p className="mt-1 leading-relaxed">
          This tool pseudonymizes text. Production HIPAA compliance also needs
          access control, TLS, audit logging, and a retention policy.
        </p>
      </div>
    </div>
  );
}
