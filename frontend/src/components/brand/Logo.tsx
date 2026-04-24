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
        <path
          d="M20 42V24a4 4 0 0 1 4-4h16a4 4 0 0 1 4 4v18l-8-5-4 3-4-3-8 5Z"
          className="fill-brand-400 dark:fill-brand-500"
        />
      </svg>
      {showWordmark && (
        <span className="font-serif text-[17px] font-semibold tracking-tight leading-none">
          Living Memory
        </span>
      )}
    </div>
  );
}
