import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowRight, Camera, Clock, Film, Image as ImageIcon, Images,
  Network, Sparkles, Upload, Wand2,
} from "lucide-react";

import Photo from "../components/media/Photo";
import { useMedia, usePersons, useStories, useVideos } from "../lib/hooks";
import { useAuthStore } from "../store/auth";

export default function DashboardPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const displayName = user?.username ?? user?.email ?? "";

  const { data: media }   = useMedia();
  const { data: persons } = usePersons();
  const { data: stories } = useStories();
  const { data: videos }  = useVideos();

  const recentPhotos   = (media   ?? []).slice(0, 8);
  const recentStories  = (stories ?? []).slice(0, 3);
  const isEmpty        = (media?.length ?? 0) === 0 && (persons?.length ?? 0) === 0 && (stories?.length ?? 0) === 0;

  const stats = [
    { label: t("dashboard.photos"),  value: media?.length   ?? 0, icon: Images,   to: "/library",  tone: "brand"   as const },
    { label: t("dashboard.people"),  value: persons?.length ?? 0, icon: Network,  to: "/family",   tone: "amber"   as const },
    { label: t("dashboard.stories"), value: stories?.length ?? 0, icon: Sparkles, to: "/stories",  tone: "emerald" as const },
    { label: t("dashboard.videos"),  value: videos?.length  ?? 0, icon: Film,     to: "/videos",   tone: "sky"     as const },
  ];

  return (
    <>
      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl border border-stone-200 bg-gradient-to-br from-amber-50 via-white to-brand-50 px-6 py-8 shadow-soft dark:border-stone-800 dark:from-amber-950/30 dark:via-stone-900 dark:to-brand-950/30 sm:px-10 sm:py-10">
        <div className="relative z-10 max-w-xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-amber-300/60 bg-white/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-amber-900 dark:border-amber-900/50 dark:bg-stone-950/60 dark:text-amber-300">
            <Sparkles className="h-3 w-3" /> Living Memory
          </span>
          <h2 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-4xl">
            {t(isEmpty ? "dashboard.heroTitleFirst" : "dashboard.heroTitle", { name: displayName })}
          </h2>
          <p className="mt-3 text-[15px] text-stone-600 dark:text-stone-300">
            {t(isEmpty ? "dashboard.heroSubFirst" : "dashboard.heroSub")}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/generate" className="btn btn-accent">
              <Wand2 className="h-4 w-4" />
              <span>{t("dashboard.writeStory")}</span>
            </Link>
            <Link to="/library" className="btn btn-ghost">
              <Upload className="h-4 w-4" />
              <span>{t("dashboard.uploadPhotos")}</span>
            </Link>
          </div>
        </div>

        {/* Decorative concentric rings on the right */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-gradient-to-br from-amber-200/50 to-brand-200/30 blur-3xl dark:from-amber-700/20 dark:to-brand-700/10"
        />
      </section>

      {/* ── Onboarding (only when archive is empty) ─────────── */}
      {isEmpty && (
        <section className="mt-6 rounded-3xl border border-stone-200 bg-white p-6 shadow-soft dark:border-stone-800 dark:bg-stone-900 sm:p-8">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h3 className="font-serif text-xl font-semibold tracking-tight">{t("dashboard.startHere")}</h3>
              <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{t("dashboard.startHereLead")}</p>
            </div>
          </div>
          <ol className="mt-6 grid gap-3 sm:grid-cols-3">
            <OnboardStep n={1} to="/library"  icon={Camera}  title={t("dashboard.step1")} body={t("dashboard.step1Body")} />
            <OnboardStep n={2} to="/family"   icon={Network} title={t("dashboard.step2")} body={t("dashboard.step2Body")} />
            <OnboardStep n={3} to="/generate" icon={Wand2}   title={t("dashboard.step3")} body={t("dashboard.step3Body")} />
          </ol>
        </section>
      )}

      {/* ── Stats ──────────────────────────────────────────── */}
      <section className="mt-6 grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4">
        {stats.map((s) => (
          <Link key={s.label} to={s.to} className="card-soft group p-5 transition hover:-translate-y-0.5 hover:shadow-lift">
            <div className="flex items-center justify-between">
              <Tone tone={s.tone}><s.icon className="h-4 w-4" /></Tone>
              <ArrowRight className="h-4 w-4 text-stone-400 transition group-hover:translate-x-0.5 group-hover:text-stone-600 dark:group-hover:text-stone-300" />
            </div>
            <p className="mt-4 font-serif text-3xl font-semibold tracking-tight">{s.value}</p>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{s.label}</p>
          </Link>
        ))}
      </section>

      {/* ── Photos + Activity (two columns on wide screens) ── */}
      <section className="mt-10 grid gap-6 lg:grid-cols-3">
        {/* Recent photos — col-span-2 on desktop */}
        <div className="lg:col-span-2">
          <div className="mb-4 flex items-end justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-500">
              {t("dashboard.recentPhotos")}
            </h3>
            <Link to="/library" className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
              {t("common.open")} →
            </Link>
          </div>
          {recentPhotos.length === 0 ? (
            <EmptyCard label={t("library.empty")} />
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
              {recentPhotos.map((m) => (
                <Link
                  key={m.id}
                  to="/library"
                  className="group relative aspect-square overflow-hidden rounded-xl border border-stone-200 bg-stone-100 dark:border-stone-800 dark:bg-stone-900"
                >
                  <Photo
                    mediaId={m.id}
                    alt={m.original_filename}
                    className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
                  />
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent activity */}
        <div>
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-500">
            {t("dashboard.recentActivity")}
          </h3>
          <ActivityFeed
            media={media   ?? []}
            stories={stories ?? []}
            videos={videos ?? []}
            emptyLabel={t("dashboard.activityEmpty")}
            labelPhoto={(name) => t("dashboard.activityPhoto", { name })}
            labelStory={(title) => t("dashboard.activityStory", { title })}
            labelVideo={t("dashboard.activityVideo")}
          />
        </div>
      </section>

      {/* ── Quick actions ──────────────────────────────────── */}
      <section className="mt-10">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-500">
          {t("dashboard.quickActions")}
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <QuickAction to="/library"  icon={Upload}  label={t("dashboard.uploadPhotos")} />
          <QuickAction to="/family"   icon={Network} label={t("dashboard.importTree")} />
          <QuickAction to="/generate" icon={Wand2}   label={t("dashboard.writeStory")} accent />
          <QuickAction to="/videos"   icon={Film}    label={t("dashboard.makeVideo")} />
        </div>
      </section>

      {/* ── Recent stories ─────────────────────────────────── */}
      <section className="mt-10 mb-4">
        <div className="mb-4 flex items-end justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-500">
            {t("dashboard.recentStories")}
          </h2>
          <Link to="/stories" className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
            {t("common.open")} →
          </Link>
        </div>
        {recentStories.length === 0 ? (
          <EmptyCard label={t("stories.empty")} />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {recentStories.map((s) => (
              <Link key={s.id} to={`/stories/${s.id}`} className="card group p-5 transition hover:-translate-y-0.5 hover:shadow-lift">
                <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-500">
                  <span className="chip chip-accent">{s.event_type}</span>
                  <span>{new Date(s.created_at).toLocaleDateString()}</span>
                </div>
                <h3 className="mt-3 font-serif text-lg font-semibold leading-snug tracking-tight line-clamp-2">
                  {s.title}
                </h3>
                <p className="mt-2 text-sm text-stone-600 line-clamp-3 dark:text-stone-400">
                  {(s.narrative ?? "").slice(0, 180)}…
                </p>
              </Link>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

// ── Helpers ─────────────────────────────────────────────────

type Tone = "brand" | "amber" | "emerald" | "sky";

function Tone({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  const map: Record<Tone, string> = {
    brand:   "bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300",
    amber:   "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    emerald: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    sky:     "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
  };
  return <span className={`inline-flex h-8 w-8 items-center justify-center rounded-lg ${map[tone]}`}>{children}</span>;
}

function QuickAction({
  to, icon: Icon, label, accent,
}: { to: string; icon: React.ComponentType<{ className?: string }>; label: string; accent?: boolean }) {
  return (
    <Link
      to={to}
      className={
        "group flex items-center gap-3 rounded-2xl border p-4 transition hover:-translate-y-0.5 " +
        (accent
          ? "border-brand-300 bg-gradient-to-br from-brand-50 to-amber-50 shadow-soft hover:shadow-lift dark:border-brand-800 dark:from-brand-950/50 dark:to-amber-950/40"
          : "border-stone-200 bg-white shadow-soft hover:shadow-lift dark:border-stone-800 dark:bg-stone-900")
      }
    >
      <span className={
        "inline-flex h-10 w-10 items-center justify-center rounded-xl " +
        (accent
          ? "bg-brand-500 text-white shadow-soft"
          : "bg-stone-100 text-stone-700 dark:bg-stone-800 dark:text-stone-300")
      }>
        <Icon className="h-5 w-5" />
      </span>
      <span className="text-sm font-medium">{label}</span>
      <ArrowRight className="ml-auto h-4 w-4 text-stone-400 transition group-hover:translate-x-0.5" />
    </Link>
  );
}

function EmptyCard({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-8 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40 dark:text-stone-500">
      {label}
    </div>
  );
}

function OnboardStep({
  n, to, icon: Icon, title, body,
}: {
  n: number; to: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string; body: string;
}) {
  return (
    <li>
      <Link
        to={to}
        className="group relative flex h-full flex-col rounded-2xl border border-stone-200 bg-stone-50/50 p-5 transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-soft dark:border-stone-800 dark:bg-stone-900/40 dark:hover:border-brand-700"
      >
        <span className="absolute -top-3 left-5 inline-flex h-7 w-7 items-center justify-center rounded-full bg-amber-500 text-xs font-bold text-white shadow-soft">
          {n}
        </span>
        <Icon className="h-5 w-5 text-stone-600 dark:text-stone-300" />
        <p className="mt-3 font-semibold leading-snug">{title}</p>
        <p className="mt-1.5 text-xs leading-relaxed text-stone-600 dark:text-stone-400">{body}</p>
        <ArrowRight className="mt-3 h-4 w-4 text-brand-500 transition group-hover:translate-x-0.5 dark:text-brand-400" />
      </Link>
    </li>
  );
}

// ── Activity feed ─────────────────────────────────────────

type ActivityItem = {
  ts:    string;        // ISO date for sorting
  kind:  "photo" | "story" | "video";
  text:  string;
  href:  string;
  icon:  React.ComponentType<{ className?: string }>;
};

function ActivityFeed({
  media, stories, videos, emptyLabel, labelPhoto, labelStory, labelVideo,
}: {
  // ``created_at`` is optional in some of the source types (MediaFile)
  // because the backend may omit it for rows still being ingested. The
  // feed below tolerates ``undefined`` by skipping the timestamp string,
  // so the looser type here matches reality.
  media:   { id: number; original_filename: string; created_at?: string }[];
  stories: { id: number; title: string; created_at: string }[];
  videos:  { id: number; created_at: string }[];
  emptyLabel: string;
  labelPhoto: (name: string) => string;
  labelStory: (title: string) => string;
  labelVideo: string;
}) {
  const items: ActivityItem[] = [
    ...media.slice(0, 5).map((m) => ({
      ts: m.created_at ?? "", kind: "photo" as const, icon: ImageIcon,
      text: labelPhoto(m.original_filename), href: "/library",
    })),
    ...stories.slice(0, 5).map((s) => ({
      ts: s.created_at, kind: "story" as const, icon: Sparkles,
      text: labelStory(s.title), href: `/stories/${s.id}`,
    })),
    ...videos.slice(0, 5).map((v) => ({
      ts: v.created_at, kind: "video" as const, icon: Film,
      text: labelVideo, href: "/videos",
    })),
  ]
    .sort((a, b) => (a.ts < b.ts ? 1 : -1))
    .slice(0, 6);

  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-4 dark:border-stone-800 dark:bg-stone-900">
      {items.length === 0 ? (
        <p className="text-sm text-stone-500 dark:text-stone-500">{emptyLabel}</p>
      ) : (
        <ul className="space-y-3">
          {items.map((it, i) => (
            <li key={i} className="flex items-start gap-3 text-sm">
              <span className="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-300">
                <it.icon className="h-3.5 w-3.5" />
              </span>
              <div className="min-w-0 flex-1">
                <Link to={it.href} className="line-clamp-1 font-medium hover:underline">{it.text}</Link>
                <p className="mt-0.5 flex items-center gap-1 text-xs text-stone-500 dark:text-stone-500">
                  <Clock className="h-3 w-3" />
                  {new Date(it.ts).toLocaleString()}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
