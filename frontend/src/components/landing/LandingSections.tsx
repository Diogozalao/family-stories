import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  BookOpen, Camera, Clock, Film, Lock,
  Network, Sparkles, Wand2, type LucideIcon,
} from "lucide-react";
import { cn } from "../../lib/utils";

/** Four headline capabilities of the system. */
export function FeaturesSection() {
  const { t } = useTranslation();
  const features: { icon: LucideIcon; title: string; body: string; tone: string }[] = [
    {
      icon: Camera,
      title: t("home.feat1Title"),
      body: t("home.feat1Body"),
      tone: "from-amber-200/60 to-amber-100/40 dark:from-amber-900/40 dark:to-amber-950/20",
    },
    {
      icon: Network,
      title: t("home.feat2Title"),
      body: t("home.feat2Body"),
      tone: "from-sky-200/60 to-sky-100/40 dark:from-sky-900/40 dark:to-sky-950/20",
    },
    {
      icon: Wand2,
      title: t("home.feat3Title"),
      body: t("home.feat3Body"),
      tone: "from-rose-200/60 to-rose-100/40 dark:from-rose-900/40 dark:to-rose-950/20",
    },
    {
      icon: Film,
      title: t("home.feat4Title"),
      body: t("home.feat4Body"),
      tone: "from-emerald-200/60 to-emerald-100/40 dark:from-emerald-900/40 dark:to-emerald-950/20",
    },
  ];

  return (
    <section id="features" className="relative px-4 py-24 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <header className="mx-auto max-w-3xl text-center">
          <span className="chip chip-accent">{t("home.featuresTag")}</span>
          <h2 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("home.featuresTitle")}
          </h2>
          <p className="mt-3 text-stone-600 dark:text-stone-400">
            {t("home.featuresLead")}
          </p>
        </header>

        <div className="mt-12 grid gap-4 sm:grid-cols-2">
          {features.map((f) => (
            <article
              key={f.title}
              className="group relative overflow-hidden rounded-3xl border border-stone-200 bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lift dark:border-stone-800 dark:bg-stone-900"
            >
              <div className={cn(
                "pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full bg-gradient-to-br blur-2xl opacity-70 transition group-hover:opacity-100",
                f.tone,
              )} />
              <div className="relative">
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900">
                  <f.icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 font-serif text-xl font-semibold tracking-tight">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-stone-600 dark:text-stone-400">{f.body}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/** Walkthrough of the four pipeline stages, with a small step-cycler. */
export function HowItWorksSection() {
  const { t } = useTranslation();
  const steps = [
    { tag: "M1", title: t("home.howStep1Title"), body: t("home.howStep1Body") },
    { tag: "M2", title: t("home.howStep2Title"), body: t("home.howStep2Body") },
    { tag: "M3", title: t("home.howStep3Title"), body: t("home.howStep3Body") },
    { tag: "M4", title: t("home.howStep4Title"), body: t("home.howStep4Body") },
  ];

  const [active, setActive] = useState(0);

  // Auto-advance every 3.5 s. Stops cycling when user clicks a step.
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (paused) return;
    const id = window.setInterval(() => setActive((i) => (i + 1) % steps.length), 3500);
    return () => window.clearInterval(id);
  }, [paused, steps.length]);

  return (
    <section id="how" className="relative bg-gradient-to-b from-transparent via-stone-100/60 to-transparent px-4 py-24 dark:via-stone-900/40 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <header className="mx-auto max-w-3xl text-center">
          <span className="chip chip-accent">{t("home.howTag")}</span>
          <h2 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("home.howTitle")}
          </h2>
        </header>

        <div className="mt-12 grid gap-8 lg:grid-cols-[1fr_1.4fr]">
          <ol className="space-y-2">
            {steps.map((s, i) => {
              const isActive = i === active;
              return (
                <li key={s.tag}>
                  <button
                    type="button"
                    onClick={() => { setActive(i); setPaused(true); }}
                    className={cn(
                      "flex w-full items-start gap-4 rounded-2xl border p-4 text-left transition",
                      isActive
                        ? "border-brand-400 bg-white shadow-soft dark:border-brand-500 dark:bg-stone-900"
                        : "border-stone-200 bg-white/60 hover:border-stone-300 dark:border-stone-800 dark:bg-stone-900/40 dark:hover:border-stone-700",
                    )}
                  >
                    <span className={cn(
                      "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg font-mono text-xs font-semibold",
                      isActive
                        ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
                        : "bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-400",
                    )}>
                      {s.tag}
                    </span>
                    <div className="min-w-0">
                      <p className="font-medium">{s.title}</p>
                      <p className={cn(
                        "mt-0.5 text-sm text-stone-600 dark:text-stone-400",
                        !isActive && "line-clamp-1",
                      )}>
                        {s.body}
                      </p>
                    </div>
                  </button>
                </li>
              );
            })}
          </ol>

          {/* Visual mock — emulates a step-by-step pipeline graphic */}
          <div className="relative overflow-hidden rounded-3xl border border-stone-200 bg-gradient-to-br from-stone-50 to-amber-50 p-8 shadow-lift dark:border-stone-800 dark:from-stone-900 dark:to-stone-950">
            <PipelineMock activeIndex={active} />
          </div>
        </div>
      </div>
    </section>
  );
}

function PipelineMock({ activeIndex }: { activeIndex: number }) {
  const { t } = useTranslation();
  const icons = [Camera, Network, Wand2, Film];
  const labels = [t("home.pipe1"), t("home.pipe2"), t("home.pipe3"), t("home.pipe4")];
  const captions = [t("home.pipeCap1"), t("home.pipeCap2"), t("home.pipeCap3"), t("home.pipeCap4")];
  return (
    <div className="flex h-full flex-col justify-center gap-6">
      <div className="flex items-center justify-between gap-3">
        {icons.map((Icon, i) => (
          <div key={i} className="flex flex-1 flex-col items-center gap-2">
            <span className={cn(
              "flex h-12 w-12 items-center justify-center rounded-2xl transition-all duration-500",
              i === activeIndex
                ? "scale-110 bg-brand-500 text-white shadow-lift"
                : i < activeIndex
                  ? "bg-emerald-500 text-white"
                  : "bg-stone-200 text-stone-500 dark:bg-stone-800 dark:text-stone-500",
            )}>
              <Icon className="h-5 w-5" />
            </span>
            <span className={cn(
              "text-[11px] uppercase tracking-wider transition",
              i === activeIndex
                ? "font-semibold text-stone-900 dark:text-stone-100"
                : "text-stone-500",
            )}>
              {labels[i]}
            </span>
          </div>
        ))}
      </div>

      <div className="relative h-1 rounded-full bg-stone-200 dark:bg-stone-800">
        <div
          className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-brand-400 to-brand-600 transition-all duration-500"
          style={{ width: `${((activeIndex + 1) / icons.length) * 100}%` }}
        />
      </div>

      <div className="rounded-2xl bg-white/70 p-5 backdrop-blur dark:bg-stone-950/40">
        <p className="font-mono text-[11px] uppercase tracking-wider text-stone-500">
          {t("home.moduleOf", { n: activeIndex + 1, total: icons.length })}
        </p>
        <p className="mt-2 font-serif text-lg font-semibold tracking-tight">
          {captions[activeIndex]}
        </p>
      </div>
    </div>
  );
}

/** Trust + privacy section — the local-first promise is the project's core. */
export function PrivacySection() {
  const { t } = useTranslation();
  const points = [
    { icon: Lock,     title: t("home.priv1Title"), body: t("home.priv1Body") },
    { icon: BookOpen, title: t("home.priv2Title"), body: t("home.priv2Body") },
    { icon: Clock,    title: t("home.priv3Title"), body: t("home.priv3Body") },
  ];
  return (
    <section id="privacy" className="relative px-4 py-24 sm:py-28">
      <div className="mx-auto max-w-5xl">
        <header className="mx-auto max-w-3xl text-center">
          <span className="chip chip-accent">{t("home.privacyTag")}</span>
          <h2 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("home.privacyTitle")}
          </h2>
          <p className="mt-3 text-stone-600 dark:text-stone-400">
            {t("home.privacyLead")}
          </p>
        </header>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {points.map((p) => (
            <div key={p.title} className="rounded-2xl border border-stone-200 bg-white p-6 dark:border-stone-800 dark:bg-stone-900">
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                <p.icon className="h-4 w-4" />
              </span>
              <p className="mt-4 font-medium">{p.title}</p>
              <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{p.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/** Final call-to-action — anchor links back to the login form at top. */
export function CTASection() {
  const { t } = useTranslation();
  return (
    <section className="relative px-4 py-24 sm:py-28">
      <div className="mx-auto max-w-3xl rounded-3xl border border-stone-200 bg-gradient-to-br from-stone-900 to-brand-900 p-10 text-center text-stone-100 shadow-lift sm:p-14 dark:border-stone-800">
        <Sparkles className="mx-auto h-7 w-7 text-brand-300" />
        <h2 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
          {t("home.ctaTitle")}
        </h2>
        <p className="mt-3 text-stone-300">
          {t("home.ctaLead")}
        </p>
        <a href="#top" className="btn btn-accent mt-8 px-6 py-3">
          {t("home.ctaButton")}
        </a>
      </div>
    </section>
  );
}
