import { useState } from "react";
import { useLocation } from "react-router-dom";
import { Menu, Moon, Sun, Monitor } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/ui/dialog";
import { VisuallyHidden } from "@/components/shared/VisuallyHidden";
import { Sidebar } from "@/components/layout/Sidebar";
import { BackendStatusPill } from "@/components/shared/BackendStatusPill";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { useSettings } from "@/lib/hooks/useSettings";
import { cn } from "@/lib/utils";

export function Topbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { settings, updateSettings } = useSettings();
  const location = useLocation();

  const currentLabel =
    NAV_ITEMS.find((item) => location.pathname.startsWith(item.to))?.label ?? "Overview";

  const cycleColorMode = () => {
    const order: typeof settings.colorMode[] = ["light", "dark", "system"];
    const next = order[(order.indexOf(settings.colorMode) + 1) % order.length];
    updateSettings({ colorMode: next });
  };

  const ModeIcon = settings.colorMode === "light" ? Sun : settings.colorMode === "dark" ? Moon : Monitor;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-border/70 bg-background/80 px-4 backdrop-blur sm:px-6">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </Button>
        <h2 className="text-sm font-semibold text-foreground sm:text-base">{currentLabel}</h2>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <BackendStatusPill className="hidden sm:inline-flex" />
        <Button
          variant="outline"
          size="icon"
          onClick={cycleColorMode}
          aria-label={`Color mode: ${settings.colorMode}. Click to change.`}
          title={`Color mode: ${settings.colorMode}`}
        >
          <ModeIcon className={cn("h-4 w-4")} />
        </Button>
      </div>

      <Dialog open={mobileOpen} onOpenChange={setMobileOpen}>
        <DialogContent className="left-0 top-0 h-full max-w-[280px] translate-x-0 translate-y-0 rounded-none border-r border-l-0 border-y-0 p-0 data-[state=closed]:slide-out-to-left data-[state=open]:slide-in-from-left sm:max-w-[300px]">
          <VisuallyHidden>
            <DialogTitle>Navigation</DialogTitle>
          </VisuallyHidden>
          <Sidebar onNavigate={() => setMobileOpen(false)} />
        </DialogContent>
      </Dialog>
    </header>
  );
}
