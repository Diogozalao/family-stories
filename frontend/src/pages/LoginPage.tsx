import { useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { AtSign, Eye, EyeOff, Loader2, LogIn } from "lucide-react";
import { useLogin } from "../lib/hooks";
import { useAuthStore } from "../store/auth";
import { extractErrorMessage } from "../lib/api";
import AuthShell from "../components/auth/AuthShell";
import LandingHeader from "../components/landing/LandingHeader";
import {
  CTASection, FeaturesSection, HowItWorksSection,
  PrivacySection, ScrollHint,
} from "../components/landing/LandingSections";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const { t } = useTranslation();
  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: { pathname?: string } } };
  const login = useLogin();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);

  // Reset both fields whenever the page becomes visible again — answers
  // "sempre que feches a página faça um reset do campo".
  useEffect(() => {
    const reset = () => {
      if (document.visibilityState === "visible") {
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

  const emailInvalid = email.length > 0 && !EMAIL_RE.test(email);
  const canSubmit = EMAIL_RE.test(email) && password.length > 0;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    login.mutate(
      { username: email, password },
      {
        onSuccess: () => {
          toast.success(t("common.success"));
          navigate(location.state?.from?.pathname ?? "/", { replace: true });
        },
        onError: (err) => toast.error(extractErrorMessage(err, t("auth.invalid"))),
      },
    );
  };

  return (
    <div id="top" className="min-h-full">
      <LandingHeader />

      <AuthShell>
        <header className="mb-7 text-center">
          <h1 className="font-serif text-3xl font-semibold tracking-tight sm:text-[2rem]">
            {t("auth.welcome")}
          </h1>
          <p className="mt-2 text-[15px] text-stone-600 dark:text-stone-400">
            {t("auth.welcomeSub")}
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="space-y-5"
          autoComplete="off"
          spellCheck={false}
        >
          {/* Honeypots that absorb the browser's autofill attempts so the
              real fields below stay empty when the user re-opens the page. */}
          <input type="text"     name="x_user_dummy" autoComplete="username"          className="hidden" tabIndex={-1} />
          <input type="password" name="x_pass_dummy" autoComplete="current-password" className="hidden" tabIndex={-1} />

          <div>
            <label className="label" htmlFor="lm-email">Email</label>
            <div className="relative">
              <AtSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
              <input
                id="lm-email"
                name="lm-email-9af2"
                autoFocus
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
              <p className="mt-1.5 text-xs text-rose-600">Indica um email válido.</p>
            )}
          </div>

          <div>
            <label className="label" htmlFor="lm-pw">{t("auth.password")}</label>
            <div className="relative">
              <input
                id="lm-pw"
                name="lm-pw-9af2"
                required
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
            <div className="mt-2 flex justify-end">
              <Link to="/forgot-password" className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">
                Esqueceste-te?
              </Link>
            </div>
          </div>

          <button
            type="submit"
            disabled={!canSubmit || login.isPending}
            className="btn btn-primary w-full justify-center py-3 text-[15px]"
          >
            {login.isPending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <LogIn className="h-5 w-5" />
            )}
            <span>{t("auth.login")}</span>
          </button>
        </form>

        <p className="mt-7 text-center text-sm text-stone-600 dark:text-stone-400">
          {t("auth.noAccount")}{" "}
          <Link to="/register" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
            {t("auth.register")}
          </Link>
        </p>

        <p className="mt-6 text-center text-xs italic text-stone-500 dark:text-stone-500">
          {t("app.tagline")}
        </p>

        <div className="mt-2 flex justify-center">
          <ScrollHint />
        </div>
      </AuthShell>

      {/* Marketing / informational sections — visible on scroll */}
      <FeaturesSection />
      <HowItWorksSection />
      <PrivacySection />
      <CTASection />
    </div>
  );
}
