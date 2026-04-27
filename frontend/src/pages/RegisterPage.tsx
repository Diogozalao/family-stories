import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import axios from "axios";
import { Eye, EyeOff, Loader2, UserPlus } from "lucide-react";
import { useRegister } from "../lib/hooks";
import { useAuthStore } from "../store/auth";
import { extractErrorMessage } from "../lib/api";
import AuthShell from "../components/auth/AuthShell";

export default function RegisterPage() {
  const { t } = useTranslation();
  const token = useAuthStore((s) => s.token);
  const navigate = useNavigate();
  const register = useRegister();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [ownerExists, setOwnerExists] = useState(false);

  if (token) return <Navigate to="/" replace />;

  const pwTooShort = password.length > 0 && password.length < 8;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pwTooShort) return;
    register.mutate(
      { username, password },
      {
        onSuccess: () => {
          toast.success(t("common.success"));
          navigate("/", { replace: true });
        },
        onError: (err) => {
          if (axios.isAxiosError(err) && err.response?.status === 409) {
            setOwnerExists(true);
            toast.error("Já existe um dono neste arquivo.");
          } else {
            toast.error(extractErrorMessage(err));
          }
        },
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

      {ownerExists && (
        <div className="mb-6 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
          <p className="font-medium">Este arquivo já tem dono.</p>
          <p className="mt-1 text-amber-800 dark:text-amber-300">
            Só podes ter uma conta por base de dados.{" "}
            <Link to="/login" className="font-semibold underline">Faz login</Link>{" "}
            com as credenciais originais, ou apaga a BD para começar de novo.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="label" htmlFor="username">{t("auth.username")}</label>
          <input
            id="username"
            autoFocus
            required
            minLength={3}
            className="input py-3 text-[15px]"
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

        <div className="rounded-xl border border-stone-200 bg-stone-50 p-3 text-xs leading-relaxed text-stone-600 dark:border-stone-800 dark:bg-stone-900/60 dark:text-stone-400">
          {t("auth.registerHint")}
        </div>

        <button
          type="submit"
          disabled={register.isPending || pwTooShort}
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
