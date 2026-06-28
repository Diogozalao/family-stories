import { cn } from "../../lib/utils";

export default function Logo({
  className,
  size = 28,
  showWordmark = true,
}: {
  className?: string;
  size?: number;
  showWordmark?: boolean;
}) {
  return (
    <div className={cn("inline-flex items-center gap-2.5", className)}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        fill="none"
        className="shrink-0"
      >
        <rect width="64" height="64" rx="14" className="fill-stone-900 dark:fill-stone-100" />
        {/* Family tree: one parent branching down to two children. */}
        <g
          className="stroke-brand-400 dark:stroke-brand-500"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M32 25 V31" />
          <path d="M21 31 H43" />
          <path d="M21 31 V38" />
          <path d="M43 31 V38" />
        </g>
        <g className="fill-brand-400 dark:fill-brand-500">
          <circle cx="32" cy="20" r="5" />
          <circle cx="21" cy="43" r="5" />
          <circle cx="43" cy="43" r="5" />
        </g>
      </svg>
      {showWordmark && (
        <span className="font-serif text-[17px] font-semibold tracking-tight leading-none">
          living_memory
        </span>
      )}
    </div>
  );
}
