import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowRight, AtSign, Brain, Eye, EyeOff, Image as ImageIcon,
  Loader2, LogIn, ShieldCheck, Sparkles,
} from "lucide-react";

import { cn } from "../../lib/utils";

interface HeroProps {
  email:         string;
  setEmail:      (v: string) => void;
  password:      string;
  setPassword:   (v: string) => void;
  showPw:        boolean;
  setShowPw:     (v: boolean) => void;
  emailInvalid:  boolean;
  canSubmit:     boolean;
  pending:       boolean;
  onSubmit:      (e: FormEvent) => void;
}

/**
 * Cloudflare-inspired split hero: marketing on the left, embedded login
 * card on the right. Both columns collapse to a single column under
 * ``lg``, with the form rendered first so the page still leads with the
 * primary action on mobile.
 */
export default function LandingHero(props: HeroProps) {
  const { t } = useTranslation();

  return (
    <section id="top" className="relative overflow-hidden pt-28 pb-20 sm:pt-32 sm:pb-24">
      <HeroBackdrop />

      <div className="relative mx-auto grid max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-[1.1fr_1fr] lg:gap-16 lg:px-10">
        {/* ── Left column ───────────────────────────────────── */}
        <div className="order-2 lg:order-1">
          <span className="inline-flex items-center gap-2 rounded-full border border-amber-300/60 bg-amber-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-300">
            <Sparkles className="h-3.5 w-3.5" />
            {t("landing.heroBadge")}
          </span>

          <h1 className="mt-5 font-serif text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-[3.5rem]">
            {t("landing.heroTitle1")}
            <span className="block text-brand-600 dark:text-brand-400">
              {t("landing.heroTitle2")}
            </span>
          </h1>

          <p className="mt-5 max-w-xl text-[15px] leading-relaxed text-stone-600 dark:text-stone-400 sm:text-base">
            {t("landing.heroLead")}
          </p>

          <ul className="mt-7 grid gap-3 sm:grid-cols-3">
            <Bullet icon={ImageIcon}    text={t("landing.heroBullet1")} />
            <Bullet icon={Brain}        text={t("landing.heroBullet2")} />
            <Bullet icon={ShieldCheck}  text={t("landing.heroBullet3")} />
          </ul>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/register" className="btn btn-accent px-5 py-3 text-[15px]">
              <span>{t("landing.getStarted")}</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/about" className="btn btn-ghost px-5 py-3 text-[15px]">
              {t("landing.learnMore")}
            </Link>
          </div>
        </div>

        {/* ── Right column: login card ──────────────────────── */}
        <div className="order-1 lg:order-2">
          <LoginCard {...props} />
        </div>
      </div>
    </section>
  );
}

function Bullet({
  icon: Icon, text,
}: { icon: React.ComponentType<{ className?: string }>; text: string }) {
  return (
    <li className="flex items-start gap-2.5 text-sm text-stone-700 dark:text-stone-300">
      <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
        <Icon className="h-3.5 w-3.5" />
      </span>
      <span>{text}</span>
    </li>
  );
}

function LoginCard({
  email, setEmail, password, setPassword, showPw, setShowPw,
  emailInvalid, canSubmit, pending, onSubmit,
}: HeroProps) {
  const { t } = useTranslation();
  return (
    <div className="relative mx-auto w-full max-w-md">
      {/* Picture-frame corners — subtle brand touch */}
      <span aria-hidden className="pointer-events-none absolute -top-1 -left-1 h-4 w-4 border-l-2 border-t-2 border-brand-400/70 dark:border-brand-500/70" />
      <span aria-hidden className="pointer-events-none absolute -top-1 -right-1 h-4 w-4 border-r-2 border-t-2 border-brand-400/70 dark:border-brand-500/70" />
      <span aria-hidden className="pointer-events-none absolute -bottom-1 -left-1 h-4 w-4 border-b-2 border-l-2 border-brand-400/70 dark:border-brand-500/70" />
      <span aria-hidden className="pointer-events-none absolute -bottom-1 -right-1 h-4 w-4 border-b-2 border-r-2 border-brand-400/70 dark:border-brand-500/70" />

      <div className="card p-7 shadow-lift backdrop-blur sm:p-8">
        <h2 className="font-serif text-2xl font-semibold tracking-tight">
          {t("auth.welcome")}
        </h2>
        <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
          {t("auth.welcomeSub")}
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4" autoComplete="off" spellCheck={false}>
          <input type="text"     name="x_user_dummy" autoComplete="username"          className="hidden" tabIndex={-1} />
          <input type="password" name="x_pass_dummy" autoComplete="current-password" className="hidden" tabIndex={-1} />

          <div>
            <label className="label" htmlFor="lm-email">Email</label>
            <div className="relative">
              <AtSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
              <input
                id="lm-email"
                name="lm-email-9af2"
                required
                type="email"
                inputMode="email"
                placeholder="email@exemplo.com"
                className="input py-3 pl-10 text-[15px]"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="off"
              />
            </div>
            {emailInvalid && (
              <p className="mt-1.5 text-xs text-rose-600">{t("auth.emailInvalid")}</p>
            )}
          </div>

          <div>
            <label className="label" htmlFor="lm-pw">{t("auth.password")}</label>
            <div className="relative">
              <input
                id="lm-pw"
                name="lm-pw-9af2"
                required
                type={showPw ? "text" : "password"}
                className="input py-3 pr-12 text-[15px]"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"
                aria-label={showPw ? "Hide password" : "Show password"}
              >
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <div className="mt-2 flex justify-end">
              <Link to="/forgot-password" className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
                {t("auth.forgotLink")}
              </Link>
            </div>
          </div>

          <button
            type="submit"
            disabled={!canSubmit || pending}
            className="btn btn-primary w-full justify-center py-3 text-[15px]"
          >
            {pending ? <Loader2 className="h-5 w-5 animate-spin" /> : <LogIn className="h-5 w-5" />}
            <span>{t("auth.login")}</span>
          </button>
        </form>

        <div className={cn("my-5 flex items-center gap-3")}>
          <span className="h-px flex-1 bg-stone-200 dark:bg-stone-800" />
          <Sparkles className="h-3.5 w-3.5 text-amber-500" />
          <span className="h-px flex-1 bg-stone-200 dark:bg-stone-800" />
        </div>

        <p className="text-center text-sm text-stone-600 dark:text-stone-400">
          {t("auth.noAccount")}{" "}
          <Link to="/register" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
            {t("auth.register")}
          </Link>
        </p>
      </div>
    </div>
  );
}

function HeroBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0">
      {/* Soft gradient orbs — Cloudflare-style atmospheric backdrop. */}
      <div className="absolute -left-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-amber-200/40 blur-3xl dark:bg-amber-700/15" />
      <div className="absolute right-0 top-1/3 h-[24rem] w-[24rem] rounded-full bg-brand-200/35 blur-3xl dark:bg-brand-700/15" />
      <div className="absolute bottom-0 left-1/3 h-[20rem] w-[20rem] rounded-full bg-rose-200/25 blur-3xl dark:bg-rose-900/15" />
      {/* Fine dot grid for texture */}
      <div
        className="absolute inset-0 opacity-[0.04] dark:opacity-[0.06]"
        style={{
          backgroundImage:  "radial-gradient(rgb(87 83 78) 1px, transparent 1px)",
          backgroundSize:   "24px 24px",
        }}
      />
    </div>
  );
}
