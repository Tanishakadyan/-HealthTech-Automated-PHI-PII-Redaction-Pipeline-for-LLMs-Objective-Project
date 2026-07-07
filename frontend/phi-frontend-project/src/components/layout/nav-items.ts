import {
  LayoutDashboard,
  ShieldOff,
  RotateCcw,
  BarChart3,
  History,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  shortcut?: string;
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/redact", label: "Redaction", icon: ShieldOff, shortcut: "⌃⏎" },
  { to: "/restore", label: "Restore", icon: RotateCcw },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/history", label: "History", icon: History },
  { to: "/settings", label: "Settings", icon: Settings },
];
