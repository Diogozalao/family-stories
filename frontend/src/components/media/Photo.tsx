import { useState } from "react";
import { ImageOff, Loader2 } from "lucide-react";

import { photoUrl } from "../../lib/photo";
import { cn } from "../../lib/utils";

interface PhotoProps {
  mediaId:   number;
  alt?:      string;
  /** Tailwind classes applied to the ``<img>`` itself. */
  className?: string;
  /** Click handler proxied to ``<img>``. */
  onClick?:  () => void;
}

/**
 * Authenticated photo with a built-in load / error UI.
 *
 * Must be placed inside a positioned wrapper (``relative``) — the
 * loading skeleton and error icon overlay the parent's bounding box,
 * keeping it visible until the bytes are decoded by the browser.
 * Without this, navigating to ``/projects`` and back to ``/library``
 * leaves blank squares for a few hundred ms while the image is being
 * fetched again.
 */
export default function Photo({ mediaId, alt = "", className, onClick }: PhotoProps) {
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");

  return (
    <>
      {state !== "ok" && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-gradient-to-br from-stone-100 to-stone-200 dark:from-stone-900 dark:to-stone-800">
          {state === "loading"
            ? <Loader2 className="h-5 w-5 animate-spin text-stone-500 dark:text-stone-400" />
            : <ImageOff className="h-6 w-6 text-stone-400 dark:text-stone-500" />}
        </div>
      )}
      <img
        src={photoUrl(mediaId)}
        alt={alt}
        loading="lazy"
        onClick={onClick}
        onLoad={() => setState("ok")}
        onError={() => setState("error")}
        className={cn(
          "transition-opacity duration-300",
          state === "ok" ? "opacity-100" : "opacity-0",
          className,
        )}
      />
    </>
  );
}
