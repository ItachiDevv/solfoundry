import { clsx } from "clsx";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

export function LoadingSpinner({
  size = "md",
  label = "Loading...",
  className,
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "h-5 w-5 border-2",
    md: "h-8 w-8 border-2",
    lg: "h-12 w-12 border-3",
  };

  return (
    <div
      className={clsx(
        "flex flex-col items-center justify-center gap-3 py-12",
        className,
      )}
    >
      <div
        className={clsx(
          "animate-spin rounded-full border-foundry-border border-t-foundry-purple",
          sizeClasses[size],
        )}
        role="status"
        aria-label={label}
      />
      {label && (
        <span className="text-sm text-foundry-text-dim">{label}</span>
      )}
    </div>
  );
}
