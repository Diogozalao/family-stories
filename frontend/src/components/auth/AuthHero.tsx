import { useTranslation } from "react-i18next";
import { BookOpen, Film, Network, Sparkles } from "lucide-react";
import Logo from "../brand/Logo";

export default function AuthHero() {
  const { t } = useTranslation();

  return (
    <aside
      aria-hidden
      className="relative hidden overflow-hidden bg-gradient-to-br from-stone-900 via-stone-900 to-brand-900 text-stone-100 lg:flex lg:flex-col lg:justify-between lg:p-12 xl:p-16"
    >
      {/* decorative orbs */}
      <div className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full bg-brand-500/30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -right-24 h-[28rem] w-[28rem] rounded-full bg-amber-400/20 blur-3xl" />
      {/* subtle grid */}
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.05]"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(255,255,255,.6) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,.6) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      <div className="relative z-10">
        <Logo />
      </div>

      <div className="relative z-10 max-w-xl">
        <h2 className="font-serif text-5xl font-semibold leading-[1.05] tracking-tight xl:text-6xl">
          Preserva as histórias da tua família — para sempre.
        </h2>
        <p className="mt-6 text-lg leading-relaxed text-stone-300">
          Carrega fotografias, importa a tua árvore genealógica e deixa a
          Living Memory escrever narrativas e montar documentários a partir
          do teu arquivo. Tudo local, tudo teu.
        </p>

        <ul className="mt-10 grid grid-cols-2 gap-4">
          <Feature icon={BookOpen} label="Histórias narradas em PT-PT" />
          <Feature icon={Network}  label="Árvore genealógica GEDCOM" />
          <Feature icon={Sparkles} label="LLM local + RAG familiar" />
          <Feature icon={Film}     label="Documentários em MP4" />
        </ul>
      </div>

      <p className="relative z-10 text-sm text-stone-400">{t("app.tagline")}</p>
    </aside>
  );
}

function Feature({
  icon: Icon, label,
}: { icon: React.ComponentType<{ className?: string }>; label: string }) {
  return (
    <li className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
      <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-500/20 text-brand-300">
        <Icon className="h-4 w-4" />
      </span>
      <span className="text-sm text-stone-200">{label}</span>
    </li>
  );
}
