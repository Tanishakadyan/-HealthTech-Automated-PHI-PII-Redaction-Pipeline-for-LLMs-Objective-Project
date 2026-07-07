import { motion } from "framer-motion";
import {
  ScanSearch,
  KeyRound,
  Timer,
  ShieldCheck,
  Gauge,
  FileJson,
} from "lucide-react";
import { useSettings } from "@/lib/hooks/useSettings";

const FEATURES = [
  {
    icon: ScanSearch,
    title: "Broad entity coverage",
    description:
      "Names via transformer NER, plus MRNs, SSNs, emails, phones, addresses, device IDs, VINs, and licensed IDs.",
  },
  {
    icon: KeyRound,
    title: "Reversible by design",
    description:
      "Every value becomes a numbered token like [NAME_001]. Restore the original text any time within the session.",
  },
  {
    icon: Timer,
    title: "Session-scoped mappings",
    description: "Placeholder maps live server-side for 30 minutes, then expire automatically.",
  },
  {
    icon: ShieldCheck,
    title: "No mapping leakage",
    description: "/redact and /restore never return the mapping table — only pseudonymized or restored text.",
  },
  {
    icon: Gauge,
    title: "Built for production",
    description: "Rate limiting, input validation, no-store headers, and optional API-key protection out of the box.",
  },
  {
    icon: FileJson,
    title: "Simple JSON API",
    description: "Two endpoints — /redact and /restore — that drop into any clinical or LLM pipeline.",
  },
];

export function FeatureGrid() {
  const { settings } = useSettings();

  return (
    <section className="border-t border-border/60 bg-muted/20 py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight">Everything de-identification needs</h2>
          <p className="mt-3 text-muted-foreground">
            Purpose-built for healthcare text, not a generic redaction toy.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, idx) => (
            <motion.div
              key={feature.title}
              initial={settings.animationsEnabled ? { opacity: 0, y: 16 } : false}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.45, delay: (idx % 3) * 0.08 }}
              className="rounded-xl border border-border/70 bg-card p-6 shadow-card"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <feature.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 font-semibold text-foreground">{feature.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
