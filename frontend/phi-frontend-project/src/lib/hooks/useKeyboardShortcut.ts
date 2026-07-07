import { useEffect } from "react";

interface ShortcutOptions {
  key: string;
  ctrlOrCmd?: boolean;
  shift?: boolean;
  onTrigger: () => void;
  enabled?: boolean;
}

export function useKeyboardShortcut({
  key,
  ctrlOrCmd = false,
  shift = false,
  onTrigger,
  enabled = true,
}: ShortcutOptions) {
  useEffect(() => {
    if (!enabled) return;

    const handler = (event: KeyboardEvent) => {
      const matchesKey = event.key.toLowerCase() === key.toLowerCase();
      const matchesModifier = ctrlOrCmd ? event.ctrlKey || event.metaKey : true;
      const matchesShift = shift ? event.shiftKey : !event.shiftKey || !shift;

      if (matchesKey && matchesModifier && matchesShift) {
        event.preventDefault();
        onTrigger();
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [key, ctrlOrCmd, shift, onTrigger, enabled]);
}
