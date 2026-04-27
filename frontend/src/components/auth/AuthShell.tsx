import type { ReactNode } from "react";
import Logo from "../brand/Logo";

/**
 * Centered premium auth layout — warm gradient backdrop, floating card
 * with subtle picture-frame corners that hint at the family-archive brand.
 */
export default function AuthShell({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div className="relative flex min-h-full items-center justify-center overflow-hidden bg-gradient-to-br from-stone-100 via-amber-50 to-brand-100 px-4 py-10 dark:from-stone-950 dark:via-stone-950 dark:to-brand-950/80">
      <Backdrop />

      <div className="relative z-10 w-full max-w-md animate-fade-in">
        <div className="mb-8 flex justify-center">
          <Logo size={36} />
        </div>

        <div className="relative">
          <FrameCorners />
          <div className="card p-8 shadow-lift backdrop-blur sm:p-10">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

function Backdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0">
      <div className="absolute left-1/2 top-0 h-[32rem] w-[32rem] -translate-x-1/2 -translate-y-1/3 rounded-full bg-brand-300/40 blur-3xl dark:bg-brand-700/30" />
      <div className="absolute bottom-0 right-0 h-[28rem] w-[28rem] translate-x-1/3 translate-y-1/3 rounded-full bg-amber-300/30 blur-3xl dark:bg-amber-900/20" />
      <div className="absolute -left-24 bottom-20 h-80 w-80 rounded-full bg-rose-200/30 blur-3xl dark:bg-stone-800/40" />
      <div
        className="absolute inset-0 opacity-[0.035] dark:opacity-[0.06]"
        style={{
          backgroundImage:
            "radial-gradient(rgb(87 83 78) 1px, transparent 1px)",
          backgroundSize: "3px 3px",
        }}
      />
    </div>
  );
}

function FrameCorners() {
  const cornerBase =
    "pointer-events-none absolute h-4 w-4 border-brand-400/70 dark:border-brand-500/70";
  return (
    <>
      <span aria-hidden className={`${cornerBase} -top-1 -left-1 border-l-2 border-t-2`} />
      <span aria-hidden className={`${cornerBase} -top-1 -right-1 border-r-2 border-t-2`} />
      <span aria-hidden className={`${cornerBase} -bottom-1 -left-1 border-b-2 border-l-2`} />
      <span aria-hidden className={`${cornerBase} -bottom-1 -right-1 border-b-2 border-r-2`} />
    </>
  );
}
