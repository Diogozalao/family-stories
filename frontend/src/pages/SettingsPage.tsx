import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  CheckCircle2, Database, Eye, EyeOff, HardDrive, KeyRound, Loader2, Moon,
  Monitor, RefreshCw, Sun, UserCircle2, XCircle, Zap,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useChangePassword, useHealth } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
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
          <div className="mt-6 border-t border-stone-100 pt-5 dark:border-stone-800">
            <ChangePasswordForm />
          </div>
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

function ChangePasswordForm() {
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [show, setShow] = useState(false);

  const tooShort = next.length > 0 && next.length < 8;
  const same = current.length > 0 && current === next;
  const canSubmit = current.length > 0 && next.length >= 8 && !same;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    change.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          toast.success("Palavra-passe alterada");
          setCurrent("");
          setNext("");
        },
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <p className="flex items-center gap-2 text-sm font-medium">
        <KeyRound className="h-4 w-4 text-stone-500" />
        Alterar palavra-passe
      </p>

      <div>
        <label className="label" htmlFor="cur-pw">Palavra-passe atual</label>
        <input
          id="cur-pw"
          type={show ? "text" : "password"}
          autoComplete="current-password"
          className="input"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
      </div>

      <div>
        <label className="label" htmlFor="new-pw">Nova palavra-passe</label>
        <div className="relative">
          <input
            id="new-pw"
            type={show ? "text" : "password"}
            autoComplete="new-password"
            minLength={8}
            className="input pr-12"
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"
            aria-label={show ? "Ocultar" : "Mostrar"}
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        <p className={cn(
          "mt-1.5 text-xs",
          tooShort || same ? "text-rose-600" : "text-stone-500 dark:text-stone-500",
        )}>
          {same
            ? "A nova palavra-passe tem de ser diferente da atual"
            : "Mínimo 8 caracteres"}
        </p>
      </div>

      <button
        type="submit"
        disabled={!canSubmit || change.isPending}
        className="btn btn-primary w-full justify-center"
      >
        {change.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
        <span>Alterar palavra-passe</span>
      </button>
    </form>
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
