import { motion } from "framer-motion";
import { useSettings } from "@/lib/hooks/useSettings";

interface Line {
  before: (string | { redact: string; token: string })[];
}

const LINES: Line[] = [
  { before: ["Patient ", { redact: "Sarah Chen", token: "NAME_001" }, " arrived at"] },
  { before: [{ redact: "Apollo General Hospital", token: "FACILITY_001" }, " on"] },
  { before: [{ redact: "03/14/1986", token: "DOB_001" }, ", MRN"] },
  { before: [{ redact: "10239481", token: "MRN_001" }, ". Contact:"] },
  { before: [{ redact: "+1 (415) 555-0148", token: "PHONE_001" }] },
];

export function RedactionShowcase() {
  const { settings } = useSettings();
  const reduced = !settings.animationsEnabled;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border/70 bg-card shadow-elevated">
      <div className="flex items-center gap-1.5 border-b border-border/70 bg-muted/40 px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-destructive/60" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#D97706]/60" />
        <span className="h-2.5 w-2.5 rounded-full bg-success/60" />
        <span className="ml-3 font-data text-xs text-muted-foreground">clinical_note.txt → /redact</span>
      </div>
      <div className="space-y-3 p-6 font-data text-sm leading-7 sm:text-base">
        {LINES.map((line, lineIdx) => (
          <p key={lineIdx} className="text-foreground/90">
            {line.before.map((part, partIdx) =>
              typeof part === "string" ? (
                <span key={partIdx}>{part}</span>
              ) : (
                <RedactedSpan
                  key={partIdx}
                  original={part.redact}
                  token={part.token}
                  delay={lineIdx * 0.9}
                  reduced={reduced}
                />
              ),
            )}
          </p>
        ))}
      </div>
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-grid opacity-40"
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.4 }}
        transition={{ duration: 1 }}
      />
    </div>
  );
}

function RedactedSpan({
  original,
  token,
  delay,
  reduced,
}: {
  original: string;
  token: string;
  delay: number;
  reduced: boolean;
}) {
  return (
    <span className="relative mx-0.5 inline-flex items-center overflow-hidden rounded px-1.5 py-0.5">
      <motion.span
        className="absolute inset-0 rounded bg-foreground/85"
        initial={{ scaleX: 0 }}
        animate={reduced ? { scaleX: 1 } : { scaleX: [0, 1, 1, 0, 0] }}
        transition={
          reduced
            ? { duration: 0.01 }
            : { duration: 5.4, times: [0, 0.08, 0.55, 0.63, 1], repeat: Infinity, delay, ease: "easeInOut" }
        }
        style={{ transformOrigin: "left" }}
      />
      <motion.span
        className="relative text-muted-foreground/0"
        animate={reduced ? { opacity: 0 } : { opacity: [0, 0, 1, 1, 0] }}
        transition={
          reduced ? { duration: 0.01 } : { duration: 5.4, times: [0, 0.08, 0.63, 0.92, 1], repeat: Infinity, delay }
        }
      >
        {original}
      </motion.span>
      <motion.span
        className="absolute inset-0 flex items-center justify-center px-1.5 py-0.5 font-semibold text-primary"
        animate={reduced ? { opacity: 1 } : { opacity: [1, 1, 0, 0, 1] }}
        transition={
          reduced ? { duration: 0.01 } : { duration: 5.4, times: [0, 0.06, 0.14, 0.98, 1], repeat: Infinity, delay }
        }
      >
        [{token}]
      </motion.span>
    </span>
  );
}
