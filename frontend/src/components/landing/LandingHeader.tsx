import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import Logo from "../brand/Logo";
import { cn } from "../../lib/utils";

const LINKS: { label: string; href: string }[] = [
  { label: "Capacidades",   href: "#features" },
  { label: "Como funciona", href: "#how"      },
  { label: "Privacidade",   href: "#privacy"  },
];

/**
 * Sticky landing header — visible on the public ``/login`` and
 * ``/register`` routes. Fades from transparent to a frosted bar once
 * the user starts scrolling so the hero stays visually clean.
 */
export default function LandingHeader() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "fixed inset-x-0 top-0 z-30 transition-all duration-300",
        scrolled
          ? "border-b border-stone-200/80 bg-stone-50/85 backdrop-blur-md shadow-soft dark:border-stone-800/80 dark:bg-stone-950/80"
          : "border-b border-transparent bg-transparent",
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
        <a href="#top" className="flex items-center gap-2 transition hover:opacity-80">
          <Logo size={28} />
        </a>

        <nav className="ml-6 hidden items-center gap-1 md:flex">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-stone-600 transition hover:bg-stone-100 hover:text-stone-900 dark:text-stone-400 dark:hover:bg-stone-900 dark:hover:text-stone-100"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/login"
            className="hidden rounded-lg px-3 py-1.5 text-sm font-medium text-stone-700 transition hover:bg-stone-100 dark:text-stone-300 dark:hover:bg-stone-900 sm:block"
          >
            Entrar
          </Link>
          <Link to="/register" className="btn btn-accent !py-1.5 !px-3 text-sm">
            <Sparkles className="h-4 w-4" />
            <span>Começar</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
