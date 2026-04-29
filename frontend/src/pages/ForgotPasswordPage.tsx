import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, AtSign, KeyRound, Loader2, Mail, MailCheck } from "lucide-react";
import AuthShell from "../components/auth/AuthShell";
import LandingHeader from "../components/landing/LandingHeader";
import { useForgotPassword } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ForgotPasswordPage() {
  const forgot = useForgotPassword();
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const emailInvalid = email.length > 0 && !EMAIL_RE.test(email);
  const canSubmit = EMAIL_RE.test(email);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    forgot.mutate(
      { email },
      {
        onSuccess: () => setSubmitted(true),
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  return (
    <div id="top" className="min-h-full">
      <LandingHeader />

      <AuthShell>
        {submitted ? (
          <SuccessState email={email} />
        ) : (
          <>
            <header className="mb-7 text-center">
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300">
                <KeyRound className="h-5 w-5" />
              </span>
              <h1 className="mt-4 font-serif text-3xl font-semibold tracking-tight sm:text-[2rem]">
                Recuperar palavra-passe
              </h1>
              <p className="mt-2 text-[15px] text-stone-600 dark:text-stone-400">
                Indica o email da tua conta. Vamos enviar-te um link seguro
                para definires uma nova palavra-passe.
              </p>
            </header>

            <form
              onSubmit={handleSubmit}
              className="space-y-5"
              autoComplete="off"
              spellCheck={false}
            >
              <div>
                <label className="label" htmlFor="fp-email">Email</label>
                <div className="relative">
                  <AtSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
                  <input
                    id="fp-email"
                    name="fp-email-9af2"
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

              <button
                type="submit"
                disabled={!canSubmit || forgot.isPending}
                className="btn btn-primary w-full justify-center py-3 text-[15px]"
              >
                {forgot.isPending ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Mail className="h-5 w-5" />
                )}
                <span>Enviar link de reset</span>
              </button>
            </form>

            <Link
              to="/login"
              className="mt-7 flex items-center justify-center gap-1.5 text-sm font-medium text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100"
            >
              <ArrowLeft className="h-4 w-4" />
              Voltar ao login
            </Link>
          </>
        )}
      </AuthShell>
    </div>
  );
}

function SuccessState({ email }: { email: string }) {
  return (
    <div className="text-center">
      <span className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
        <MailCheck className="h-6 w-6" />
      </span>
      <h1 className="mt-5 font-serif text-3xl font-semibold tracking-tight sm:text-[2rem]">
        Verifica o teu email
      </h1>
      <p className="mt-3 text-[15px] text-stone-600 dark:text-stone-400">
        Se existir uma conta com{" "}
        <span className="font-medium text-stone-900 dark:text-stone-100">{email}</span>,
        enviámos para lá um link para definir uma nova palavra-passe.
      </p>
      <p className="mt-2 text-xs text-stone-500 dark:text-stone-500">
        O link expira em 60 minutos. Verifica também a pasta de spam.
      </p>

      <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-left text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
        <p className="font-medium">Modo local-first</p>
        <p className="mt-1 text-amber-800 dark:text-amber-300">
          Se o servidor SMTP não estiver configurado, o link foi escrito no
          log do backend (<code className="font-mono text-[11px]">logs/launcher/backend.log</code>).
          Procura por <code className="font-mono text-[11px]">email_disabled_falling_back_to_log</code>.
        </p>
      </div>

      <Link
        to="/login"
        className="mt-7 flex items-center justify-center gap-1.5 text-sm font-medium text-stone-600 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100"
      >
        <ArrowLeft className="h-4 w-4" />
        Voltar ao login
      </Link>
    </div>
  );
}
