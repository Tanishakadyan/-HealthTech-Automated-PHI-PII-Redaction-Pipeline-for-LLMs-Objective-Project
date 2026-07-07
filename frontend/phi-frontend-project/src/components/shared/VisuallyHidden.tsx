import * as React from "react";

/**
 * Visually hides content while keeping it available to assistive tech.
 * Used to satisfy Radix's requirement that Dialog/AlertDialog always have
 * an accessible title, even when we don't want one shown visually.
 */
export const VisuallyHidden = React.forwardRef<HTMLSpanElement, React.HTMLAttributes<HTMLSpanElement>>(
  ({ style, ...props }, ref) => (
    <span
      ref={ref}
      style={{
        position: "absolute",
        border: 0,
        width: 1,
        height: 1,
        padding: 0,
        margin: -1,
        overflow: "hidden",
        clip: "rect(0, 0, 0, 0)",
        whiteSpace: "nowrap",
        wordWrap: "normal",
        ...style,
      }}
      {...props}
    />
  ),
);
VisuallyHidden.displayName = "VisuallyHidden";
