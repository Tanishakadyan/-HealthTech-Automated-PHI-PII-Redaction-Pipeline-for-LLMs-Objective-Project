const STACK = [
  "React 19",
  "TypeScript",
  "Vite",
  "Tailwind CSS",
  "shadcn/ui",
  "TanStack Query",
  "FastAPI",
  "Transformer NER",
  "Presidio",
];

export function TechStackSection() {
  return (
    <section className="py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <p className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Built on a modern, typed stack
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {STACK.map((tech) => (
            <span
              key={tech}
              className="rounded-full border border-border/70 bg-card px-4 py-2 text-sm font-medium text-foreground/80 shadow-subtle"
            >
              {tech}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
