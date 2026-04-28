import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowRight, Film, Images, Network, Sparkles, Upload, Wand2,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useAuthStore } from "../store/auth";
import { useMedia, usePersons, useStories, useVideos } from "../lib/hooks";
import { photoUrl } from "../lib/photo";

export default function DashboardPage() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);

  const { data: media } = useMedia();
  const { data: persons } = usePersons();
  const { data: stories } = useStories();
  const { data: videos } = useVideos();

  const recentPhotos = (media ?? []).slice(0, 6);
  const recentStories = (stories ?? []).slice(0, 3);

  const stats = [
    { label: t("dashboard.photos"),  value: media?.length ?? 0,   icon: Images,  to: "/library",  tone: "brand" },
    { label: t("dashboard.people"),  value: persons?.length ?? 0, icon: Network, to: "/family",   tone: "amber" },
    { label: t("dashboard.stories"), value: stories?.length ?? 0, icon: Sparkles, to: "/stories", tone: "emerald" },
    { label: t("dashboard.videos"),  value: videos?.length ?? 0,  icon: Film,     to: "/videos",  tone: "sky" },
  ] as const;

  return (
    <>
      <PageHeader
        title={t("dashboard.greeting", { name: user?.username ?? "" })}
        subtitle={t("dashboard.subtitle")}
        actions={
          <Link to="/generate" className="btn btn-accent">
            <Wand2 className="h-4 w-4" />
            <span>{t("dashboard.writeStory")}</span>
          </Link>
        }
      />

      {/* Stats */}
      <section className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-4">
        {stats.map((s) => (
          <Link key={s.label} to={s.to} className="card-soft group p-5 transition hover:-translate-y-0.5 hover:shadow-lift">
            <div className="flex items-center justify-between">
              <Tone tone={s.tone}>
                <s.icon className="h-4 w-4" />
              </Tone>
              <ArrowRight className="h-4 w-4 text-stone-400 transition group-hover:translate-x-0.5 group-hover:text-stone-600 dark:group-hover:text-stone-300" />
            </div>
            <p className="mt-4 font-serif text-3xl font-semibold tracking-tight">{s.value}</p>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{s.label}</p>
          </Link>
        ))}
      </section>

      {/* Quick actions */}
      <section className="mt-10">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-500">
          {t("dashboard.quickActions")}
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <QuickAction to="/library"  icon={Upload}    label={t("dashboard.uploadPhotos")} />
          <QuickAction to="/family"   icon={Network}   label={t("dashboard.importTree")} />
          <QuickAction to="/generate" icon={Wand2}     label={t("dashboard.writeStory")} accent />
          <QuickAction to="/videos"   icon={Film}      label={t("dashboard.makeVideo")} />
        </div>
      </section>

      {/* Recent photos */}
      <section className="mt-10">
        <div className="mb-4 flex items-end justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-500">
            {t("dashboard.recentPhotos")}
          </h2>
          <Link to="/library" className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
            {t("common.open")} →
          </Link>
        </div>
        {recentPhotos.length === 0 ? (
          <EmptyCard label={t("library.empty")} />
        ) : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-6">
            {recentPhotos.map((m) => (
              <Link
                key={m.id}
                to="/library"
                className="group relative aspect-square overflow-hidden rounded-xl border border-stone-200 bg-stone-100 dark:border-stone-800 dark:bg-stone-900"
              >
                <img
                  src={photoUrl(m.id)}
                  alt={m.original_filename}
                  loading="lazy"
                  className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
                />
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Recent stories */}
      <section className="mt-10">
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

function Tone({ tone, children }: { tone: "brand" | "amber" | "emerald" | "sky"; children: React.ReactNode }) {
  const map: Record<typeof tone, string> = {
    brand: "bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300",
    amber: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    emerald: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
    sky: "bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300",
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
