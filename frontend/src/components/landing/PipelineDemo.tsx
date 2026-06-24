import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  BookOpen, Calendar, Camera, Film, MapPin, Play, Sparkles,
} from "lucide-react";
import { cn } from "../../lib/utils";

/**
 * Interactive "watch a memory come alive" demo for the public landing.
 *
 * Auto-advances through the four pipeline stages (photo → AI describes →
 * narrative writes itself → video), and lets the visitor click any stage.
 * The AI description and the narrative are typed out live, so the page
 * *shows* the product instead of just describing it. Pure CSS transitions
 * + state (no extra deps) keep it consistent with the rest of the landing.
 */

const STAGE_ICONS = [Camera, Sparkles, BookOpen, Film];
const STAGE_COUNT = 4;

function useTypewriter(text: string, active: boolean, speed = 26): string {
  const [out, setOut] = useState("");
  useEffect(() => {
    if (!active) { setOut(""); return; }
    setOut("");
    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      setOut(text.slice(0, i));
      if (i >= text.length) window.clearInterval(id);
    }, speed);
    return () => window.clearInterval(id);
  }, [text, active, speed]);
  return out;
}

export default function PipelineDemo() {
  const { t } = useTranslation();
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const stages = [
    t("pipelineDemo.stage1"), t("pipelineDemo.stage2"),
    t("pipelineDemo.stage3"), t("pipelineDemo.stage4"),
  ];

  useEffect(() => {
    if (paused) return;
    const id = window.setInterval(
      () => setActive((i) => (i + 1) % STAGE_COUNT),
      4200,
    );
    return () => window.clearInterval(id);
  }, [paused]);

  return (
    <section id="demo" className="relative px-4 py-24 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <header className="mx-auto max-w-3xl text-center">
          <span className="chip chip-accent">{t("pipelineDemo.tag")}</span>
          <h2 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            {t("pipelineDemo.title")}
          </h2>
          <p className="mt-3 text-stone-600 dark:text-stone-400">
            {t("pipelineDemo.lead")}
          </p>
        </header>

        <div className="mt-12 grid gap-6 lg:grid-cols-[260px_1fr]">
          {/* Stage tabs */}
          <ol className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
            {stages.map((label, i) => {
              const Icon = STAGE_ICONS[i];
              const isActive = i === active;
              const done = i < active;
              return (
                <li key={label} className="shrink-0 lg:shrink">
                  <button
                    type="button"
                    onClick={() => { setActive(i); setPaused(true); }}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition",
                      isActive
                        ? "border-brand-400 bg-white shadow-soft dark:border-brand-500 dark:bg-stone-900"
                        : "border-stone-200 bg-white/60 hover:border-stone-300 dark:border-stone-800 dark:bg-stone-900/40 dark:hover:border-stone-700",
                    )}
                  >
                    <span className={cn(
                      "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl transition",
                      isActive
                        ? "bg-brand-500 text-white shadow-soft"
                        : done
                          ? "bg-emerald-500 text-white"
                          : "bg-stone-100 text-stone-500 dark:bg-stone-800 dark:text-stone-400",
                    )}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className={cn(
                      "text-sm font-medium",
                      isActive ? "text-stone-900 dark:text-stone-100" : "text-stone-600 dark:text-stone-400",
                    )}>
                      {label}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>

          {/* Stage canvas */}
          <div className="relative min-h-[320px] overflow-hidden rounded-3xl border border-stone-200 bg-gradient-to-br from-stone-50 to-amber-50 p-6 shadow-lift dark:border-stone-800 dark:from-stone-900 dark:to-stone-950 sm:p-8">
            <div className="absolute inset-x-0 top-0 h-1 bg-stone-200/70 dark:bg-stone-800">
              <div
                className="h-full bg-gradient-to-r from-brand-400 to-brand-600 transition-all duration-500"
                style={{ width: `${((active + 1) / STAGE_COUNT) * 100}%` }}
              />
            </div>
            {/* keyed wrapper re-triggers the fade + remounts the typewriters */}
            <div key={active} className="animate-fade-in">
              <StageCanvas active={active} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function StageCanvas({ active }: { active: number }) {
  const { t } = useTranslation();
  const tags  = t("pipelineDemo.tags",  { returnObjects: true }) as string[];
  const chips = t("pipelineDemo.chips", { returnObjects: true }) as string[];
  const desc = useTypewriter(t("pipelineDemo.description"), active === 1);
  const narrative = useTypewriter(t("pipelineDemo.narrative"), active === 2);

  if (active === 0) {
    return (
      <div className="flex flex-col items-center justify-center pt-4">
        <PhotoFrame />
        <p className="mt-5 text-center text-sm text-stone-600 dark:text-stone-400">
          {t("pipelineDemo.step0Hint")}
        </p>
      </div>
    );
  }

  if (active === 1) {
    return (
      <div className="grid gap-5 pt-3 sm:grid-cols-[180px_1fr] sm:items-center">
        <PhotoFrame compact />
        <div>
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400">
            <Sparkles className="h-3.5 w-3.5" /> Gemini Vision
          </div>
          <p className="mt-2 min-h-[64px] font-serif text-lg leading-snug text-stone-900 dark:text-stone-100">
            {desc}
            <span className="ml-0.5 inline-block h-5 w-0.5 -translate-y-0.5 animate-pulse bg-brand-500 align-middle" />
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {tags.map((tag) => (
              <span key={tag} className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-600 dark:bg-stone-800 dark:text-stone-300">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (active === 2) {
    const first = narrative.slice(0, 1);
    const rest = narrative.slice(1);
    return (
      <div className="pt-3">
        <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-brand-600 dark:text-brand-400">
          <BookOpen className="h-3.5 w-3.5" /> {t("pipelineDemo.aiStory")}
        </div>
        <div className="mt-3 rounded-2xl bg-white/70 p-5 shadow-soft dark:bg-stone-950/40">
          <p className="font-serif text-lg leading-relaxed text-stone-900 dark:text-stone-100">
            {first && (
              <span className="float-left mr-2 mt-1 font-serif text-4xl font-semibold leading-none text-brand-600 dark:text-brand-400">
                {first}
              </span>
            )}
            {rest}
            <span className="ml-0.5 inline-block h-5 w-0.5 -translate-y-0.5 animate-pulse bg-brand-500 align-middle" />
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center pt-2">
      <VideoFrame />
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {chips.map((c) => (
          <span key={c} className="rounded-full border border-stone-200 bg-white/70 px-3 py-1 text-xs text-stone-600 dark:border-stone-700 dark:bg-stone-900/60 dark:text-stone-300">
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}

function PhotoFrame({ compact = false }: { compact?: boolean }) {
  return (
    <div className={cn(
      "relative aspect-[4/3] w-full overflow-hidden rounded-2xl border-4 border-white bg-gradient-to-br from-amber-200 via-rose-200 to-sky-200 shadow-lift dark:border-stone-800 dark:from-amber-900/50 dark:via-rose-900/40 dark:to-sky-900/40",
      compact ? "max-w-[180px]" : "max-w-[260px]",
    )}>
      <div className="absolute inset-0 flex items-center justify-center">
        <Camera className="h-10 w-10 text-white/70" />
      </div>
      <div className="absolute bottom-2 left-2 flex flex-wrap gap-1">
        <span className="inline-flex items-center gap-1 rounded-md bg-black/40 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur">
          <Calendar className="h-2.5 w-2.5" /> 2014
        </span>
        <span className="inline-flex items-center gap-1 rounded-md bg-black/40 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur">
          <MapPin className="h-2.5 w-2.5" /> GPS
        </span>
      </div>
    </div>
  );
}

function VideoFrame() {
  const { t } = useTranslation();
  const [prog, setProg] = useState(0);
  useEffect(() => {
    setProg(0);
    const id = window.setInterval(() => setProg((x) => (x >= 100 ? 0 : x + 1.4)), 60);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="relative aspect-video w-full max-w-md overflow-hidden rounded-2xl border border-stone-800 bg-gradient-to-br from-stone-900 to-stone-950 shadow-lift">
      {/* subtle "Ken Burns" drifting backdrop */}
      <div className="absolute inset-0 bg-gradient-to-tr from-amber-500/10 via-transparent to-sky-500/10" />
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="flex h-14 w-14 items-center justify-center rounded-full bg-white/90 text-stone-900 shadow-lift">
          <Play className="ml-0.5 h-6 w-6 fill-current" />
        </span>
      </div>
      {/* lower-third caption */}
      <div className="absolute bottom-8 left-4 right-4">
        <div className="inline-block rounded-md bg-black/50 px-2 py-1 font-serif text-sm text-white backdrop-blur">
          {t("pipelineDemo.caption")}
        </div>
      </div>
      {/* timeline / playhead */}
      <div className="absolute inset-x-3 bottom-3 h-1 rounded-full bg-white/20">
        <div className="h-full rounded-full bg-brand-400" style={{ width: `${prog}%` }} />
        <div className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow" style={{ left: `${prog}%` }} />
      </div>
    </div>
  );
}
