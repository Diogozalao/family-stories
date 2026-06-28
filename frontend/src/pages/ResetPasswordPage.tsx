import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  Check, CheckCircle2, Eye, EyeOff, KeyRound, Loader2, ShieldAlert, X,
} from "lucide-react";
import AuthShell from "../components/auth/AuthShell";
import LandingHeader from "../components/landing/LandingHeader";
import { useResetPassword } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
import { supabase } from "../lib/supabase";
import { cn } from "../lib/utils";

export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const reset = useResetPassword();

  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [done, setDone] = useState(false);
  // The email link drops the user here with a ``#access_token=`` URL
  // fragment; Supabase swaps that for a session asynchronously. We
  // gate the form on that session existing so the "Link inválido" view
  // only appears when the recovery handshake truly failed.
  const [sessionState, setSessionState] = useState<"checking" | "ready" | "missing">("checking");

  useEffect(() => {
    setPw("");
    setConfirm("");
  }, []);

  useEffect(() => {
    let cancelled = false;
    supabase.auth.getSession().then(({ data }) => {
      if (cancelled) return;
      setSessionState(data.session ? "ready" : "missing");
    });
    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "PASSWORD_RECOVERY" || (event === "SIGNED_IN" && session)) {
        setSessionState("ready");
      }
    });
    return () => {
      cancelled = true;
      sub.subscription.unsubscribe();
    };
  }, []);

  // Same password policy as the registration form.
  const pwRules = [
    { label: t("auth.passwordReqLength"), ok: pw.length >= 8 },
    { label: t("auth.passwordReqUpper"),  ok: /[A-Z]/.test(pw) },
    { label: t("auth.passwordReqLower"),  ok: /[a-z]/.test(pw) },
    { label: t("auth.passwordReqDigit"),  ok: /[0-9]/.test(pw) },
  ];
  const pwValid   = pwRules.every((r) => r.ok);
  const mismatch  = confirm.length > 0 && confirm !== pw;
  const canSubmit = sessionState === "ready" && pwValid && confirm === pw;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    reset.mutate(
      { new_password: pw },
      {
        onSuccess: async () => {
          setDone(true);
          toast.success(t("resetPassword.updated"));
          // Sign out so the user lands on the login form with the new
          // credentials, rather than staying in the recovery session.
          await supabase.auth.signOut();
          setTimeout(() => navigate("/login", { replace: true }), 2500);
        },
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  return (
    <div id="top" className="min-h-full">
      <LandingHeader />

      <AuthShell>
        {sessionState === "checking" ? (
          <Checking />
        ) : sessionState === "missing" ? (
          <InvalidToken />
        ) : done ? (
          <DoneState />
        ) : (
          <>
            <header className="mb-7 text-center">
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                <KeyRound className="h-5 w-5" />
              </span>
              <h1 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-[2rem]">
                {t("resetPassword.title")}
              </h1>
              <p className="mt-2 text-[15px] text-stone-600 dark:text-stone-400">
                {t("resetPassword.lead")}
              </p>
            </header>

            <form
              onSubmit={handleSubmit}
              className="space-y-5"
              autoComplete="off"
              spellCheck={false}
            >
              <div>
                <label className="label" htmlFor="rp-pw">{t("settings.newPassword")}</label>
                <div className="relative">
                  <input
                    id="rp-pw"
                    type={show ? "text" : "password"}
                    required
                    minLength={8}
                    autoFocus
                    className="input py-3 pr-12 text-[15px]"
                    value={pw}
                    onChange={(e) => setPw(e.target.value)}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShow((v) => !v)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"
                    aria-label={show ? t("settings.hide") : t("settings.show")}
                  >
                    {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                <ul className="mt-2 space-y-1">
                  <li className="mb-1 text-xs font-medium text-stone-500 dark:text-stone-500">
                    {t("auth.passwordReqTitle")}
                  </li>
                  {pwRules.map((r) => (
                    <li
                      key={r.label}
                      className={cn(
                        "flex items-center gap-1.5 text-xs",
                        r.ok ? "text-emerald-600 dark:text-emerald-400" : "text-stone-500 dark:text-stone-500",
                      )}
                    >
                      {r.ok ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5 text-stone-400" />}
                      <span>{r.label}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <label className="label" htmlFor="rp-pw2">{t("resetPassword.confirmLabel")}</label>
                <input
                  id="rp-pw2"
                  type={show ? "text" : "password"}
                  required
                  className="input py-3 text-[15px]"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  autoComplete="new-password"
                />
                {mismatch && (
                  <p className="mt-1.5 text-xs text-rose-600">{t("resetPassword.mismatch")}</p>
                )}
              </div>

              <button
                type="submit"
                disabled={!canSubmit || reset.isPending}
                className="btn btn-primary w-full justify-center py-3 text-[15px]"
              >
                {reset.isPending ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <KeyRound className="h-5 w-5" />
                )}
                <span>{t("resetPassword.submit")}</span>
              </button>
            </form>
          </>
        )}
      </AuthShell>
    </div>
  );
}

function Checking() {
  const { t } = useTranslation();
  return (
    <div className="text-center">
      <Loader2 className="mx-auto h-6 w-6 animate-spin text-stone-500" />
      <p className="mt-4 text-sm text-stone-500">{t("resetPassword.validating")}</p>
    </div>
  );
}

function InvalidToken() {
  const { t } = useTranslation();
  return (
    <div className="text-center">
      <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300">
        <ShieldAlert className="h-6 w-6" />
      </span>
      <h1 className="mt-5 font-serif text-3xl font-semibold tracking-tight sm:text-[2rem]">
        {t("resetPassword.invalidTitle")}
      </h1>
      <p className="mt-3 text-[15px] text-stone-600 dark:text-stone-400">
        {t("resetPassword.invalidBody")}
      </p>
      <Link to="/forgot-password" className="btn btn-primary mt-6">
        {t("resetPassword.requestNew")}
      </Link>
    </div>
  );
}

function DoneState() {
  const { t } = useTranslation();
  return (
    <div className="text-center">
      <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
        <CheckCircle2 className="h-6 w-6" />
      </span>
      <h1 className="mt-5 font-serif text-3xl font-semibold tracking-tight sm:text-[2rem]">
        {t("resetPassword.updated")}
      </h1>
      <p className="mt-3 text-[15px] text-stone-600 dark:text-stone-400">
        {t("resetPassword.redirecting")}
      </p>
    </div>
  );
}
