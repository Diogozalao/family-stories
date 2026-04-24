import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Eye, EyeOff, Loader2, LogIn } from "lucide-react";
import Logo from "../components/brand/Logo";
import { useLogin } from "../lib/hooks";
import { useAuthStore } from "../store/auth";
import { extractErrorMessage } from "../lib/api";
import AuthHero from "../components/auth/AuthHero";

export default function LoginPage() {
  const { t } = useTranslation();
  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: { pathname?: string } } };
  const login = useLogin();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);

  if (token) return <Navigate to="/" replace />;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login.mutate(
      { username, password },
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
    <div className="grid min-h-full bg-stone-50 dark:bg-stone-950 lg:grid-cols-2">
      <AuthHero />

      <section className="relative flex items-center justify-center px-6 py-12 sm:px-10 lg:px-16">
        <div className="w-full max-w-lg">
          <div className="mb-10 flex justify-center lg:hidden">
            <Logo size={32} />
          </div>

          <header className="mb-8">
            <h1 className="font-serif text-4xl font-semibold tracking-tight sm:text-5xl">
              {t("auth.welcome")}
            </h1>
            <p className="mt-3 text-base text-stone-600 dark:text-stone-400">
              {t("auth.welcomeSub")}
            </p>
          </header>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="label" htmlFor="username">{t("auth.username")}</label>
              <input
                id="username"
                autoFocus
                required
                className="input text-base py-3"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </div>

            <div>
              <label className="label" htmlFor="password">{t("auth.password")}</label>
              <div className="relative">
                <input
                  id="password"
                  required
                  type={showPw ? "text" : "password"}
                  className="input text-base py-3 pr-12"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
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
            </div>

            <button
              type="submit"
              disabled={login.isPending}
              className="btn btn-primary w-full justify-center py-3 text-base"
            >
              {login.isPending ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <LogIn className="h-5 w-5" />
              )}
              <span>{t("auth.login")}</span>
            </button>
          </form>

          <p className="mt-8 text-center text-sm text-stone-600 dark:text-stone-400">
            {t("auth.noAccount")}{" "}
            <Link to="/register" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
              {t("auth.register")}
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
