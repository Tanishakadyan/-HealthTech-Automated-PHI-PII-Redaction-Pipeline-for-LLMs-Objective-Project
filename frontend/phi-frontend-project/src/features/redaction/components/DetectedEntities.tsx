import { motion } from "framer-motion";
import { ShieldQuestion } from "lucide-react";
import type { RedactionResponse } from "@/lib/types/api";
import { ENTITY_COUNT_KEYS } from "@/lib/types/api";
import { EntityBadge } from "@/components/shared/EntityBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { useSettings } from "@/lib/hooks/useSettings";

export function DetectedEntities({ response }: { response: RedactionResponse | null }) {
  const { settings } = useSettings();

  if (!response) {
    return (
      <EmptyState
        icon={ShieldQuestion}
        title="No detections yet"
        description="Run a redaction to see which entity types were found and how many of each."
      />
    );
  }

  const detected = ENTITY_COUNT_KEYS.map((key) => ({ key, count: response[key] })).filter(
    (entry) => entry.count > 0,
  );

  if (detected.length === 0) {
    return (
      <EmptyState
        icon={ShieldQuestion}
        title="Nothing detected"
        description="No PHI/PII patterns matched in this text."
      />
    );
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {detected.map((entry, idx) => (
        <motion.div
          key={entry.key}
          initial={settings.animationsEnabled ? { opacity: 0, y: 8 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: idx * 0.04 }}
        >
          <EntityBadge entityKey={entry.key} count={entry.count} />
        </motion.div>
      ))}
    </div>
  );
}
