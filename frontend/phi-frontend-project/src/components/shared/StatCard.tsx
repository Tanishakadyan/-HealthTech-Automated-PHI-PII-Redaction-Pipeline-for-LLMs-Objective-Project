import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatNumber } from "@/lib/utils";
import { useSettings } from "@/lib/hooks/useSettings";

interface StatCardProps {
  label: string;
  value: number;
  icon: LucideIcon;
  accentColor?: string;
  delay?: number;
  suffix?: string;
}

export function StatCard({ label, value, icon: Icon, accentColor = "#0891B2", delay = 0, suffix }: StatCardProps) {
  const { settings } = useSettings();

  return (
    <motion.div
      initial={settings.animationsEnabled ? { opacity: 0, y: 12 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="relative overflow-hidden">
        <div
          className="absolute -right-6 -top-6 h-20 w-20 rounded-full opacity-10"
          style={{ backgroundColor: accentColor }}
          aria-hidden
        />
        <CardContent className="flex items-start justify-between p-5">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className="mt-1.5 font-data text-2xl font-semibold tracking-tight">
              {formatNumber(value)}
              {suffix && <span className="ml-1 text-sm font-normal text-muted-foreground">{suffix}</span>}
            </p>
          </div>
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
            style={{ backgroundColor: `${accentColor}1A`, color: accentColor }}
          >
            <Icon className="h-4.5 w-4.5" />
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
