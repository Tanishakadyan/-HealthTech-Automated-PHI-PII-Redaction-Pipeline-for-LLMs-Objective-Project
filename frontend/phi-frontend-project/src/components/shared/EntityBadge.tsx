import type { EntityCountKey } from "@/lib/types/api";
import { ENTITY_META } from "@/lib/constants/entities";
import { cn } from "@/lib/utils";

export function EntityBadge({
  entityKey,
  count,
  className,
}: {
  entityKey: EntityCountKey;
  count: number;
  className?: string;
}) {
  const meta = ENTITY_META[entityKey];
  const Icon = meta.icon;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border border-border/70 bg-card px-3 py-2 text-sm",
        className,
      )}
    >
      <span
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md"
        style={{ backgroundColor: `${meta.color}1A`, color: meta.color }}
      >
        <Icon className="h-3.5 w-3.5" />
      </span>
      <span className="flex-1 truncate text-foreground/90">{meta.label}</span>
      <span className="font-data text-sm font-semibold">{count}</span>
    </div>
  );
}
