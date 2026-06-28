import { cn } from "../../lib/utils";

export default function Logo({
  className,
  size = 38,
  showWordmark = true,
}: {
  className?: string;
  size?: number;
  showWordmark?: boolean;
}) {
  return (
    <div className={cn("inline-flex items-center gap-2.5", className)}>
      {/* Brand mark: the tree image lives at frontend/public/logo.png */}
      <img
        src="/logo.png"
        width={size}
        height={size}
        alt="Living memory"
        className="shrink-0 object-contain"
      />
      {showWordmark && (
        <span className="font-serif text-[19px] font-semibold tracking-tight leading-none">
          Living memory
        </span>
      )}
    </div>
  );
}
