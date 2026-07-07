import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function CtaSection() {
  return (
    <section className="border-t border-border/60 py-20">
      <div className="mx-auto max-w-3xl px-4 text-center sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold tracking-tight">Ready to redact your first note?</h2>
        <p className="mt-3 text-muted-foreground">
          Paste clinical text, get a pseudonymized version back in milliseconds, restore it whenever you need to.
        </p>
        <div className="mt-8">
          <Button size="lg" asChild>
            <Link to="/redact">
              Open the redaction workspace <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
