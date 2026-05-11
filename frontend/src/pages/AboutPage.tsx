import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowRight, BookOpenText, Brain, Camera, Heart, Image as ImageIcon,
  Network, ShieldCheck, Sparkles, Users, Video,
} from "lucide-react";

import LandingHeader from "../components/landing/LandingHeader";

/**
 * Public "About" page — explains what Living Memory / Family Stories
 * actually *is* and why someone should care. Reachable both from the
 * landing nav and (later) from inside the authenticated app.
 */
export default function AboutPage() {
  const { t } = useTranslation();

  return (
    <div id="top" className="min-h-screen bg-stone-50 dark:bg-stone-950">
      <LandingHeader />

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-20 sm:pt-40 sm:pb-28">
        <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-amber-300/50 bg-amber-50 px-3 py-1 text-xs font-medium uppercase tracking-wider text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-300">
            <Heart className="h-3.5 w-3.5" /> {t("about.tag")}
          </span>
          <h1 className="mt-6 font-serif text-4xl font-semibold tracking-tight sm:text-5xl">
            {t("about.heroTitle")}
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-stone-600 dark:text-stone-400">
            {t("about.heroLead")}
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <Link to="/register" className="btn btn-accent">
              <Sparkles className="h-4 w-4" />
              <span>{t("about.cta")}</span>
            </Link>
            <Link to="/login" className="btn btn-ghost">
              <span>{t("auth.login")}</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Mission ──────────────────────────────────────────────── */}
      <section className="border-t border-stone-200 bg-white py-20 dark:border-stone-800 dark:bg-stone-900/50">
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
            <div>
              <h2 className="font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
                {t("about.missionTitle")}
              </h2>
              <p className="mt-5 text-[15px] leading-relaxed text-stone-600 dark:text-stone-400">
                {t("about.missionP1")}
              </p>
              <p className="mt-4 text-[15px] leading-relaxed text-stone-600 dark:text-stone-400">
                {t("about.missionP2")}
              </p>
            </div>
            <ul className="grid gap-4">
              <Pillar icon={Heart}        title={t("about.pillar1Title")} body={t("about.pillar1Body")} />
              <Pillar icon={BookOpenText} title={t("about.pillar2Title")} body={t("about.pillar2Body")} />
              <Pillar icon={ShieldCheck}  title={t("about.pillar3Title")} body={t("about.pillar3Body")} />
            </ul>
          </div>
        </div>
      </section>

      {/* ── Pipeline ─────────────────────────────────────────────── */}
      <section className="py-20">
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <header className="mx-auto max-w-2xl text-center">
            <h2 className="font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
              {t("about.pipelineTitle")}
            </h2>
            <p className="mt-4 text-[15px] leading-relaxed text-stone-600 dark:text-stone-400">
              {t("about.pipelineLead")}
            </p>
          </header>

          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <Step n={1} icon={Camera}  title={t("about.step1Title")} body={t("about.step1Body")} />
            <Step n={2} icon={Network} title={t("about.step2Title")} body={t("about.step2Body")} />
            <Step n={3} icon={Brain}   title={t("about.step3Title")} body={t("about.step3Body")} />
            <Step n={4} icon={Video}   title={t("about.step4Title")} body={t("about.step4Body")} />
          </div>
        </div>
      </section>

      {/* ── Who is this for ──────────────────────────────────────── */}
      <section className="border-t border-stone-200 bg-stone-100/60 py-20 dark:border-stone-800 dark:bg-stone-900/30">
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <header className="mx-auto max-w-2xl text-center">
            <h2 className="font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
              {t("about.audienceTitle")}
            </h2>
            <p className="mt-4 text-[15px] leading-relaxed text-stone-600 dark:text-stone-400">
              {t("about.audienceLead")}
            </p>
          </header>
          <div className="mt-12 grid gap-4 sm:grid-cols-3">
            <Audience icon={Users}     title={t("about.aud1Title")} body={t("about.aud1Body")} />
            <Audience icon={ImageIcon} title={t("about.aud2Title")} body={t("about.aud2Body")} />
            <Audience icon={Heart}     title={t("about.aud3Title")} body={t("about.aud3Body")} />
          </div>
        </div>
      </section>

      {/* ── CTA footer ───────────────────────────────────────────── */}
      <section className="py-24">
        <div className="mx-auto max-w-2xl px-4 text-center sm:px-6">
          <h2 className="font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("about.ctaTitle")}
          </h2>
          <p className="mt-4 text-[15px] text-stone-600 dark:text-stone-400">
            {t("about.ctaLead")}
          </p>
          <Link to="/register" className="btn btn-accent mt-8">
            <Sparkles className="h-4 w-4" />
            <span>{t("about.cta")}</span>
          </Link>
        </div>
      </section>
    </div>
  );
}

function Pillar({
  icon: Icon, title, body,
}: { icon: React.ComponentType<{ className?: string }>; title: string; body: string }) {
  return (
    <li className="flex gap-4 rounded-2xl border border-stone-200 bg-white p-5 shadow-soft dark:border-stone-800 dark:bg-stone-900">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
        <Icon className="h-5 w-5" />
      </span>
      <div>
        <p className="font-semibold">{title}</p>
        <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{body}</p>
      </div>
    </li>
  );
}

function Step({
  n, icon: Icon, title, body,
}: { n: number; icon: React.ComponentType<{ className?: string }>; title: string; body: string }) {
  return (
    <div className="relative rounded-2xl border border-stone-200 bg-white p-5 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lift dark:border-stone-800 dark:bg-stone-900">
      <span className="absolute -top-3 left-5 inline-flex h-7 w-7 items-center justify-center rounded-full bg-amber-500 text-xs font-bold text-white shadow-soft">
        {n}
      </span>
      <Icon className="h-6 w-6 text-stone-600 dark:text-stone-300" />
      <p className="mt-3 font-semibold">{title}</p>
      <p className="mt-1.5 text-sm text-stone-600 dark:text-stone-400">{body}</p>
    </div>
  );
}

function Audience({
  icon: Icon, title, body,
}: { icon: React.ComponentType<{ className?: string }>; title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-6 text-center shadow-soft dark:border-stone-800 dark:bg-stone-900">
      <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-200">
        <Icon className="h-6 w-6" />
      </span>
      <p className="mt-4 font-semibold">{title}</p>
      <p className="mt-1.5 text-sm text-stone-600 dark:text-stone-400">{body}</p>
    </div>
  );
}
