import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  AlertTriangle, Bell, CheckCircle2, Database, Eye, EyeOff,
  HardDrive, Info, KeyRound, Loader2, Moon, Monitor, Palette,
  RefreshCw, ShieldAlert, Sun, Trash2, UserCircle2, XCircle, Zap,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import {
  useChangePassword, useDeleteAccount, useHealth, useIndexFacts,
} from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
import { useAuthStore } from "../store/auth";
import { useThemeStore, type ThemeMode } from "../store/theme";
import { setLanguage } from "../i18n";
import { cn } from "../lib/utils";

type Section = "account" | "appearance" | "notifications" | "system" | "danger";

const SECTIONS: { id: Section; label: string; icon: typeof UserCircle2 }[] = [
  { id: "account",       label: "Conta",         icon: UserCircle2 },
  { id: "appearance",    label: "Aparência",     icon: Palette },
  { id: "notifications", label: "Notificações",  icon: Bell },
  { id: "system",        label: "Sistema",       icon: Database },
  { id: "danger",        label: "Zona de perigo", icon: ShieldAlert },
];

export default function SettingsPage() {
  const { t } = useTranslation();
  const [active, setActive] = useState<Section>("account");

  return (
    <>
      <PageHeader title={t("settings.title")} subtitle={t("settings.subtitle")} />

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <SideNav active={active} onChange={setActive} />

        <div>
          {active === "account"       && <AccountSection />}
          {active === "appearance"    && <AppearanceSection />}
          {active === "notifications" && <NotificationsSection />}
          {active === "system"        && <SystemSection />}
          {active === "danger"        && <DangerSection />}
        </div>
      </div>
    </>
  );
}

// ── Sidebar de secções ──────────────────────────────────────────────────────

function SideNav({ active, onChange }: { active: Section; onChange: (s: Section) => void }) {
  return (
    <nav className="flex flex-col gap-1 lg:sticky lg:top-24 lg:self-start">
      {SECTIONS.map((s) => {
        const isActive = active === s.id;
        const isDanger = s.id === "danger";
        return (
          <button
            key={s.id}
            onClick={() => onChange(s.id)}
            className={cn(
              "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition",
              isActive
                ? isDanger
                  ? "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300"
                  : "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
                : isDanger
                  ? "text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/30"
                  : "text-stone-600 hover:bg-stone-100 dark:text-stone-400 dark:hover:bg-stone-900",
            )}
          >
            <s.icon className="h-4 w-4" />
            <span>{s.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

// ── Conta ───────────────────────────────────────────────────────────────────

function AccountSection() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);

  return (
    <div className="space-y-6">
      <Card title="Perfil" icon={UserCircle2}>
        <dl className="space-y-3 text-sm">
          <Field label={t("auth.name")}  value={user?.username ?? "—"} />
          <Field label="Email"           value={user?.email ?? "—"} />
          <Field label="ID"              value={user?.id ?? "—"} mono />
        </dl>
      </Card>

      <Card title="Segurança" icon={KeyRound}>
        <ChangePasswordForm />
      </Card>
    </div>
  );
}

// ── Aparência ───────────────────────────────────────────────────────────────

function AppearanceSection() {
  const { t, i18n } = useTranslation();
  const mode = useThemeStore((s) => s.mode);
  const setMode = useThemeStore((s) => s.setMode);

  return (
    <div className="space-y-6">
      <Card title="Tema" icon={Palette}>
        <p className="mb-4 text-sm text-stone-600 dark:text-stone-400">
          A opção <strong>Sistema</strong> segue automaticamente o que tens definido no SO.
        </p>
        <div className="grid grid-cols-3 gap-2">
          <ThemeBtn current={mode} value="light"  onClick={setMode} icon={Sun}     label={t("settings.light")} />
          <ThemeBtn current={mode} value="dark"   onClick={setMode} icon={Moon}    label={t("settings.dark")} />
          <ThemeBtn current={mode} value="system" onClick={setMode} icon={Monitor} label={t("settings.system")} />
        </div>
      </Card>

      <Card title="Idioma" icon={Info}>
        <div className="grid grid-cols-2 gap-2">
          <LangBtn active={i18n.language === "pt"} onClick={() => setLanguage("pt")} flag="🇵🇹" label="Português" />
          <LangBtn active={i18n.language === "en"} onClick={() => setLanguage("en")} flag="🇬🇧" label="English" />
        </div>
      </Card>
    </div>
  );
}

// ── Notificações ────────────────────────────────────────────────────────────

function NotificationsSection() {
  const [taskToasts, setTaskToasts] = useState(
    () => localStorage.getItem("lm-pref-task-toasts") !== "false",
  );

  const toggle = () => {
    const next = !taskToasts;
    setTaskToasts(next);
    localStorage.setItem("lm-pref-task-toasts", String(next));
    toast.success(`Notificações ${next ? "ativadas" : "desligadas"} (recarrega a página para aplicar)`);
  };

  return (
    <div className="space-y-6">
      <Card title="Notificações em segundo plano" icon={Bell}>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Avisar quando uma tarefa termina</p>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
              Mostra uma notificação no canto sempre que uma geração de história ou vídeo for concluída.
            </p>
          </div>
          <Toggle on={taskToasts} onClick={toggle} />
        </div>
      </Card>
    </div>
  );
}

// ── Sistema ─────────────────────────────────────────────────────────────────

function SystemSection() {
  const { t } = useTranslation();
  const { data: health, refetch, isFetching } = useHealth();
  const reindex = useIndexFacts();

  return (
    <div className="space-y-6">
      <Card title={t("settings.health")} icon={Database} action={
        <button onClick={() => refetch()} disabled={isFetching} className="btn btn-ghost">
          <RefreshCw className={cn("h-4 w-4", isFetching && "animate-spin")} />
          <span>{t("settings.checkAgain")}</span>
        </button>
      }>
        {health && (
          <>
            <div className="mb-4 flex items-center gap-2">
              <OverallBadge status={health.status} />
              <span className="text-sm text-stone-500 dark:text-stone-500">
                {health.status === "ok" ? t("settings.healthOk")
                  : health.status === "degraded" ? t("settings.healthDegraded")
                    : t("settings.healthError")}
              </span>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {Object.entries(health.checks ?? {}).map(([key, info]) => (
                <CheckRow key={key} name={key} status={String(info.status)} />
              ))}
            </div>
          </>
        )}
      </Card>

      <Card title="Manutenção" icon={Zap}>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Reindexar factos no RAG</p>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
              Útil depois de carregar muitas fotos novas — o ChromaDB volta a vetorizar tudo do zero.
            </p>
          </div>
          <button
            onClick={() => reindex.mutate(undefined, {
              onSuccess: () => toast.success("Reindex completo"),
              onError: (err) => toast.error(extractErrorMessage(err)),
            })}
            disabled={reindex.isPending}
            className="btn btn-outline"
          >
            {reindex.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            <span>Reindexar</span>
          </button>
        </div>
      </Card>

      <Card title="Sobre" icon={Info}>
        <dl className="space-y-3 text-sm">
          <Field label="Aplicação" value="Living Memory" />
          <Field label="Versão" value="0.3.0" mono />
          <Field label="Backend" value="FastAPI + SQLite + Celery" />
          <Field label="LLM local" value="Llama 3.1 (Ollama)" />
          <Field label="Modo de email" value={import.meta.env.VITE_SMTP_NOTE ?? "Local-first (log-only por defeito)"} />
        </dl>
      </Card>
    </div>
  );
}

// ── Zona de perigo ──────────────────────────────────────────────────────────

function DangerSection() {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-rose-200 bg-rose-50/60 p-1 dark:border-rose-900/40 dark:bg-rose-950/20">
        <Card title="Eliminar conta" icon={AlertTriangle} tone="rose">
          <DeleteAccountForm />
        </Card>
      </div>
    </div>
  );
}

function DeleteAccountForm() {
  const navigate = useNavigate();
  const del = useDeleteAccount();
  const [open, setOpen] = useState(false);
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);

  const canSubmit = pw.length > 0 && confirm.trim() === "APAGAR";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    del.mutate(
      { current_password: pw, confirm: confirm.trim() },
      {
        onSuccess: () => {
          toast.success("Conta e dados eliminados.");
          navigate("/register", { replace: true });
        },
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  if (!open) {
    return (
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-rose-800 dark:text-rose-300">
          Apaga a tua conta, todas as fotografias, histórias, vídeos, projetos
          e tarefas. <strong>Não há undo.</strong>
        </p>
        <button onClick={() => setOpen(true)} className="btn shrink-0 bg-rose-600 text-white hover:bg-rose-700">
          <Trash2 className="h-4 w-4" />
          <span>Eliminar conta…</span>
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="rounded-xl border border-rose-300 bg-rose-100/80 p-4 text-sm text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-200">
        Esta operação é <strong>irreversível</strong>. Vais perder todas as
        fotografias carregadas, histórias geradas, vídeos e projetos.
      </div>

      <div>
        <label className="label" htmlFor="del-pw">Confirma com a tua palavra-passe</label>
        <div className="relative">
          <input
            id="del-pw"
            type={show ? "text" : "password"}
            required
            className="input pr-12"
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            autoComplete="current-password"
          />
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <div>
        <label className="label" htmlFor="del-confirm">
          Escreve <span className="font-mono text-rose-700 dark:text-rose-300">APAGAR</span> em maiúsculas
        </label>
        <input
          id="del-confirm"
          required
          className="input font-mono"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="APAGAR"
        />
      </div>

      <div className="flex items-center justify-end gap-2">
        <button type="button" onClick={() => { setOpen(false); setPw(""); setConfirm(""); }} className="btn btn-ghost">
          Cancelar
        </button>
        <button
          type="submit"
          disabled={!canSubmit || del.isPending}
          className="btn bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50"
        >
          {del.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          <span>Eliminar tudo</span>
        </button>
      </div>
    </form>
  );
}

// ── Componentes auxiliares ─────────────────────────────────────────────────

function Card({
  title, icon: Icon, action, children, tone = "default",
}: {
  title: string;
  icon: typeof UserCircle2;
  action?: React.ReactNode;
  children: React.ReactNode;
  tone?: "default" | "rose";
}) {
  return (
    <section className={cn(
      "card p-6",
      tone === "rose" && "border-rose-200 dark:border-rose-900/40",
    )}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <h2 className={cn(
          "flex items-center gap-2 font-serif text-lg font-semibold tracking-tight",
          tone === "rose" && "text-rose-800 dark:text-rose-300",
        )}>
          <Icon className="h-5 w-5 text-stone-500" />
          {title}
        </h2>
        {action}
      </div>
      {children}
    </section>
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
        "flex flex-col items-center gap-1.5 rounded-xl border p-4 transition",
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

function Toggle({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative h-6 w-11 shrink-0 rounded-full transition",
        on ? "bg-brand-500" : "bg-stone-300 dark:bg-stone-700",
      )}
      aria-pressed={on}
    >
      <span className={cn(
        "absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-soft transition-transform",
        on ? "translate-x-5" : "translate-x-0.5",
      )} />
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

function CheckRow({ name, status }: { name: string; status: string }) {
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

// ── Mudar palavra-passe (extraído do ficheiro original) ────────────────────

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
          {same ? "A nova palavra-passe tem de ser diferente da atual" : "Mínimo 8 caracteres"}
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
