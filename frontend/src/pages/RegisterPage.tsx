import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { AtSign, Eye, EyeOff, Loader2, User as UserIcon, UserPlus } from "lucide-react";
import { useRegister } from "../lib/hooks";
import { useAuthStore } from "../store/auth";
import { extractErrorMessage } from "../lib/api";
import AuthShell from "../components/auth/AuthShell";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function RegisterPage() {
  const { t } = useTranslation();
  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();
  const register = useRegister();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [needsEmailConfirm, setNeedsEmailConfirm] = useState(false);

  useEffect(() => {
    const reset = () => {
      if (document.visibilityState === "visible") {
        setUsername("");
        setEmail("");
        setPassword("");
      }
    };
    document.addEventListener("visibilitychange", reset);
    window.addEventListener("pageshow", reset);
    return () => {
      document.removeEventListener("visibilitychange", reset);
      window.removeEventListener("pageshow", reset);
    };
  }, []);

  if (token) return <Navigate to="/" replace />;

  const pwTooShort   = password.length > 0 && password.length < 8;
  const emailInvalid = email.length > 0 && !EMAIL_RE.test(email);
  const nameTooShort = username.length > 0 && username.trim().length < 2;
  const canSubmit    = username.trim().length >= 2 && EMAIL_RE.test(email) && password.length >= 8;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    register.mutate(
      { email, password, username: username.trim() },
      {
        onSuccess: (data) => {
          // When "Confirm email" is enabled in Supabase, the SDK returns
          // ``data.session === null`` and the user gets an email with
          // the verification link. We surface a friendly note instead
          // of pretending the signup is complete.
          if (data?.session) {
            toast.success(t("common.success"));
            navigate("/", { replace: true });
          } else {
            setNeedsEmailConfirm(true);
            toast.success(t("auth.accountCreated"));
          }
        },
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  return (
    <AuthShell>
      <header className="mb-7 text-center">
        <h1 className="font-serif text-3xl font-semibold tracking-tight sm:text-[2rem]">
          {t("auth.registerTitle")}
        </h1>
        <p className="mt-2 text-[15px] text-stone-600 dark:text-stone-400">
          {t("auth.registerSub")}
        </p>
      </header>

      {needsEmailConfirm && (
        <div className="mb-6 rounded-2xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-200">
          <p className="font-medium">{t("auth.checkEmailTitle")}</p>
          <p className="mt-1 text-emerald-800 dark:text-emerald-300">
            {t("auth.checkEmailBody")}{" "}
            <Link to="/login" className="font-semibold underline">{t("auth.login")}</Link>.
          </p>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="space-y-5"
        autoComplete="off"
        spellCheck={false}
      >
        <input type="text"     name="x_user_dummy" autoComplete="username"          className="hidden" tabIndex={-1} />
        <input type="password" name="x_pass_dummy" autoComplete="new-password"     className="hidden" tabIndex={-1} />

        <div>
          <label className="label" htmlFor="reg-name">{t("auth.name")}</label>
          <div className="relative">
            <UserIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
            <input
              id="reg-name"
              name="reg-name-9af2"
              autoFocus
              required
              minLength={2}
              type="text"
              placeholder={t("auth.namePlaceholder")}
              className="input py-3 pl-10 text-[15px]"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="off"
            />
          </div>
          {nameTooShort && (
            <p className="mt-1.5 text-xs text-rose-600">{t("auth.nameTooShort")}</p>
          )}
        </div>

        <div>
          <label className="label" htmlFor="reg-email">Email</label>
          <div className="relative">
            <AtSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
            <input
              id="reg-email"
              name="reg-email-9af2"
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
          <label className="label" htmlFor="reg-pw">{t("auth.password")}</label>
          <div className="relative">
            <input
              id="reg-pw"
              name="reg-pw-9af2"
              required
              minLength={8}
              type={showPw ? "text" : "password"}
              className="input py-3 pr-12 text-[15px]"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
            />
            <button
              type="button"
              onClick={() => setShowPw((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800"
              aria-label={showPw ? "Hide password" : "Show password"}
            >
              {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <p className={`mt-2 text-xs ${pwTooShort ? "text-rose-600" : "text-stone-500 dark:text-stone-500"}`}>
            {t("auth.passwordHint")}
          </p>
        </div>

        <button
          type="submit"
          disabled={!canSubmit || register.isPending}
          className="btn btn-primary w-full justify-center py-3 text-[15px]"
        >
          {register.isPending ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <UserPlus className="h-5 w-5" />
          )}
          <span>{t("auth.register")}</span>
        </button>
      </form>

      <p className="mt-7 text-center text-sm text-stone-600 dark:text-stone-400">
        {t("auth.haveAccount")}{" "}
        <Link to="/login" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
          {t("auth.login")}
        </Link>
      </p>
    </AuthShell>
  );
}
