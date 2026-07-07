import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight, Lock, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BackendStatusPill } from "@/components/shared/BackendStatusPill";
import { RedactionShowcase } from "@/features/landing/components/RedactionShowcase";
import { useSettings } from "@/lib/hooks/useSettings";

export function Hero() {
  const { settings } = useSettings();
  const initial = settings.animationsEnabled ? { opacity: 0, y: 16 } : false;

  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-grid [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,black,transparent)]" />
      <div className="mx-auto grid max-w-7xl gap-12 px-4 pb-20 pt-16 sm:px-6 lg:grid-cols-2 lg:items-center lg:px-8 lg:pt-24">
        <div>
          <motion.div
            initial={initial}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground"
          >
            <Sparkles className="h-3.5 w-3.5 text-primary" />
            Reversible pseudonymization for clinical text
          </motion.div>

          <motion.h1
            initial={initial}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.05 }}
            className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-[3.25rem] lg:leading-[1.05]"
          >
            De-identify PHI before it ever reaches an LLM.
          </motion.h1>

          <motion.p
            initial={initial}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.12 }}
            className="mt-5 max-w-lg text-lg leading-relaxed text-muted-foreground"
          >
            PHI Guard detects names, MRNs, phone numbers, facilities, SSNs and
            more in clinical text, swaps each for a reversible pseudonym token,
            and restores the original only when you need it — server-side,
            session-scoped, never logged.
          </motion.p>

          <motion.div
            initial={initial}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.18 }}
            className="mt-8 flex flex-wrap items-center gap-3"
          >
            <Button size="lg" asChild>
              <Link to="/redact">
                Start redacting <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link to="/dashboard">View dashboard</Link>
            </Button>
          </motion.div>

          <motion.div
            initial={initial}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.24 }}
            className="mt-8 flex flex-wrap items-center gap-3"
          >
            <BackendStatusPill />
            <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
              <Lock className="h-3.5 w-3.5" /> Mappings never leave the server
            </span>
          </motion.div>
        </div>

        <motion.div
          initial={settings.animationsEnabled ? { opacity: 0, scale: 0.96 } : false}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
        >
          <RedactionShowcase />
        </motion.div>
      </div>
    </section>
  );
}
