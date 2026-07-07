import { Link } from "react-router-dom";
import { ShieldOff, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-4 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <ShieldOff className="h-8 w-8" />
      </div>
      <p className="mt-6 font-data text-sm font-semibold uppercase tracking-widest text-muted-foreground">
        404 [PAGE_NOT_FOUND]
      </p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">This route was redacted</h1>
      <p className="mt-2 max-w-sm text-muted-foreground">
        The page you're looking for doesn't exist, or the link was mistyped.
      </p>
      <Button className="mt-8" asChild>
        <Link to="/">
          <ArrowLeft /> Back to home
        </Link>
      </Button>
    </div>
  );
}
