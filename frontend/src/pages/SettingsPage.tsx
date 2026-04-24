import { useTranslation } from "react-i18next";
import {
  CheckCircle2, Database, HardDrive, Moon, Monitor, RefreshCw,
  Sun, UserCircle2, XCircle, Zap,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useHealth } from "../lib/hooks";
import { useAuthStore } from "../store/auth";
import { useThemeStore, type ThemeMode } from "../store/theme";
import { setLanguage } from "../i18n";
import { cn } from "../lib/utils";

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const mode = useThemeStore((s) => s.mode);
  const setMode = useThemeStore((s) => s.setMode);
  const { data: health, refetch, isFetching } = useHealth();

  return (
    <>
      <PageHeader title={t("settings.title")} subtitle={t("settings.subtitle")} />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Account */}
        <section className="card p-6">
          <h2 className="flex items-center gap-2 font-serif text-lg font-semibold tracking-tight">
            <UserCircle2 className="h-5 w-5 text-stone-500" />
            {t("settings.account")}
          </h2>
          <dl className="mt-5 space-y-3 text-sm">
            <Field label={t("auth.username")} value={user?.username ?? "—"} />
            <Field label="ID" value={user?.id?.toString() ?? "—"} mono />
            <Field label="Owner" value={user?.is_owner ? t("common.yes") : t("common.no")} />
          </dl>
        </section>

        {/* Appearance */}
        <section className="card p-6">
          <h2 className="font-serif text-lg font-semibold tracking-tight">
            {t("settings.appearance")}
          </h2>

          <div className="mt-5">
            <p className="label">{t("settings.theme")}</p>
            <div className="grid grid-cols-3 gap-2">
              <ThemeBtn current={mode} value="light" onClick={setMode} icon={Sun}    label={t("settings.light")} />
              <ThemeBtn current={mode} value="dark"  onClick={setMode} icon={Moon}   label={t("settings.dark")} />
              <ThemeBtn current={mode} value="system" onClick={setMode} icon={Monitor} label={t("settings.system")} />
            </div>
          </div>

          <div className="mt-6">
            <p className="label">{t("settings.language")}</p>
            <div className="grid grid-cols-2 gap-2">
              <LangBtn active={i18n.language === "pt"} onClick={() => setLanguage("pt")} flag="🇵🇹" label="Português" />
              <LangBtn active={i18n.language === "en"} onClick={() => setLanguage("en")} flag="🇬🇧" label="English" />
            </div>
          </div>
        </section>

        {/* Health */}
        <section className="card p-6 lg:col-span-2">
          <div className="flex items-center justify-between">
            <h2 className="font-serif text-lg font-semibold tracking-tight">
              {t("settings.health")}
            </h2>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="btn btn-ghost"
            >
              <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
              <span>{t("settings.checkAgain")}</span>
            </button>
          </div>

          {health && (
            <>
              <div className="mt-4 flex items-center gap-2">
                <OverallBadge status={health.status} />
                <span className="text-sm text-stone-500 dark:text-stone-500">
                  {health.status === "ok" ? t("settings.healthOk")
                    : health.status === "degraded" ? t("settings.healthDegraded")
                      : t("settings.healthError")}
                </span>
              </div>

              <div className="mt-5 grid gap-2 sm:grid-cols-2">
                {Object.entries(health.checks ?? {}).map(([key, info]) => (
                  <CheckRow key={key} name={key} status={String(info.status)} detail={info} />
                ))}
              </div>
            </>
          )}
        </section>
      </div>
    </>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-stone-100 pb-2 last:border-0 dark:border-stone-800">
      <dt className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-500">{label}</dt>
      <dd className={cn("truncate", mono && "font-mono text-xs")}>{value}</dd>
    </div>
  );
}

function ThemeBtn({
  current, value, onClick, icon: Icon, label,
}: {
  current: ThemeMode;
  value: ThemeMode;
  onClick: (m: ThemeMode) => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  const active = current === value;
  return (
    <button
      onClick={() => onClick(value)}
      className={cn(
        "flex flex-col items-center gap-1.5 rounded-xl border p-3 transition",
        active
          ? "border-brand-400 bg-brand-50/60 dark:border-brand-500 dark:bg-brand-950/30"
          : "border-stone-200 bg-white hover:border-stone-300 dark:border-stone-800 dark:bg-stone-900 dark:hover:border-stone-700",
      )}
    >
      <Icon className={cn("h-5 w-5", active ? "text-brand-600 dark:text-brand-400" : "text-stone-500")} />
      <span className="text-xs font-medium">{label}</span>
    </button>
  );
}

function LangBtn({
  active, onClick, flag, label,
}: { active: boolean; onClick: () => void; flag: string; label: string }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-xl border p-3 transition",
        active
          ? "border-brand-400 bg-brand-50/60 dark:border-brand-500 dark:bg-brand-950/30"
          : "border-stone-200 bg-white hover:border-stone-300 dark:border-stone-800 dark:bg-stone-900 dark:hover:border-stone-700",
      )}
    >
      <span className="text-lg" aria-hidden>{flag}</span>
      <span className="text-sm font-medium">{label}</span>
    </button>
  );
}

function OverallBadge({ status }: { status: "ok" | "degraded" | "error" }) {
  const map = {
    ok: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    degraded: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    error: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300",
  } as const;
  const Icon = status === "ok" ? CheckCircle2 : status === "error" ? XCircle : Zap;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wider ${map[status]}`}>
      <Icon className="h-3.5 w-3.5" />
      {status}
    </span>
  );
}

function CheckRow({ name, status }: { name: string; status: string; detail: unknown }) {
  const { t } = useTranslation();
  const ok = status === "ok" || status === "available" || status === "healthy";
  const Icon = ok ? CheckCircle2 : XCircle;
  const labelKey = `health.${name}`;
  const label = t(labelKey, { defaultValue: name });
  const IconMap: Record<string, React.ComponentType<{ className?: string }>> = {
    database: Database,
    disk: HardDrive,
  };
  const Leader = IconMap[name] ?? Zap;

  return (
    <div className="flex items-center gap-3 rounded-xl border border-stone-200 bg-white p-3 dark:border-stone-800 dark:bg-stone-900">
      <Leader className="h-4 w-4 text-stone-400" />
      <span className="flex-1 text-sm">{label}</span>
      <span className={cn(
        "inline-flex items-center gap-1 text-xs font-medium",
        ok ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400",
      )}>
        <Icon className="h-3.5 w-3.5" />
        {status}
      </span>
    </div>
  );
}
