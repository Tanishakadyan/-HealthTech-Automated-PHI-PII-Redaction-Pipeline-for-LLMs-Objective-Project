import { Toaster as Sonner } from "sonner";
import { useSettings } from "@/lib/hooks/useSettings";

type ToasterProps = React.ComponentProps<typeof Sonner>;

function Toaster({ ...props }: ToasterProps) {
  const { resolvedDark } = useSettings();

  return (
    <Sonner
      theme={resolvedDark ? "dark" : "light"}
      className="toaster group"
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-card group-[.toaster]:text-card-foreground group-[.toaster]:border-border group-[.toaster]:shadow-elevated",
          description: "group-[.toast]:text-muted-foreground",
          actionButton: "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton: "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
