import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, Check, Loader2, Sparkles } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useGenerateNarrative, useIndexFacts, usePersons, useTemplates } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
import { cn, initials } from "../lib/utils";

type Step = 1 | 2 | 3 | 4;

export default function GeneratePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: templates } = useTemplates();
  const { data: persons } = usePersons();
  const gen = useGenerateNarrative();
  const index = useIndexFacts();

  const [step, setStep] = useState<Step>(1);
  const [eventType, setEventType] = useState<string>("default");
  const [title, setTitle] = useState("");
  const [query, setQuery] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [mode, setMode] = useState<"sync" | "background">("background");

  const valid = useMemo(() => {
    if (step === 1) return !!eventType;
    if (step === 3) return title.trim().length >= 3 && query.trim().length >= 5;
    return true;
  }, [step, eventType, title, query]);

  const togglePerson = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const handleGenerate = () => {
    gen.mutate(
      {
        title: title.trim(),
        event_type: eventType,
        query: query.trim(),
        person_ids: selectedIds,
        mode,
      },
      {
        onSuccess: (data: any) => {
          if (mode === "sync" && data?.id) {
            navigate(`/stories/${data.id}`);
          } else {
            toast.success(t("videos.processing"));
            navigate("/tasks");
          }
        },
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  return (
    <>
      <PageHeader
        title={t("generate.title")}
        subtitle={t("generate.subtitle")}
        actions={
          <button
            onClick={() => index.mutate(undefined, {
              onSuccess: () => toast.success(t("common.success")),
              onError: (err) => toast.error(extractErrorMessage(err)),
            })}
            disabled={index.isPending}
            className="btn btn-ghost"
            title="Reindex facts"
          >
            {index.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            <span>Reindex</span>
          </button>
        }
      />

      <Stepper step={step} />

      <div className="card p-6 sm:p-8 mt-6">
        {step === 1 && (
          <div>
            <h2 className="font-serif text-xl font-semibold tracking-tight">{t("generate.step1")}</h2>
            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {(templates ?? [{ id: "default", name: "Memória Familiar", tone: "nostalgic", structure: "" }]).map((tpl) => (
                <button
                  key={tpl.id}
                  onClick={() => setEventType(tpl.id)}
                  className={cn(
                    "rounded-2xl border p-4 text-left transition",
                    eventType === tpl.id
                      ? "border-brand-400 bg-brand-50/60 ring-2 ring-brand-200 dark:border-brand-500 dark:bg-brand-950/30 dark:ring-brand-900/40"
                      : "border-stone-200 bg-white hover:border-stone-300 dark:border-stone-800 dark:bg-stone-900 dark:hover:border-stone-700",
                  )}
                >
                  <p className="font-medium">{tpl.name}</p>
                  <p className="mt-1 text-xs uppercase tracking-wider text-stone-500 dark:text-stone-500">{tpl.tone}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 className="font-serif text-xl font-semibold tracking-tight">{t("generate.step2")}</h2>
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{t("generate.selectPeople")}</p>
            <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {(persons ?? []).map((p) => {
                const active = selectedIds.includes(p.id);
                return (
                  <button
                    key={p.id}
                    onClick={() => togglePerson(p.id)}
                    className={cn(
                      "flex items-center gap-3 rounded-xl border p-3 text-left transition",
                      active
                        ? "border-brand-400 bg-brand-50/60 dark:border-brand-500 dark:bg-brand-950/30"
                        : "border-stone-200 bg-white hover:border-stone-300 dark:border-stone-800 dark:bg-stone-900",
                    )}
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-xs font-semibold text-white">
                      {initials(p.name)}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm">{p.name}</span>
                    {active && <Check className="h-4 w-4 text-brand-600 dark:text-brand-400" />}
                  </button>
                );
              })}
            </div>
            {(persons ?? []).length === 0 && (
              <p className="mt-4 text-sm text-stone-500">{t("family.noTree")}</p>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5">
            <h2 className="font-serif text-xl font-semibold tracking-tight">{t("generate.step3")}</h2>
            <div>
              <label className="label">{t("generate.storyTitle")}</label>
              <input
                className="input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={t("generate.storyTitlePlaceholder")}
              />
            </div>
            <div>
              <label className="label">{t("generate.queryLabel")}</label>
              <textarea
                className="input min-h-[140px] resize-y"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t("generate.queryPlaceholder")}
              />
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-5">
            <h2 className="font-serif text-xl font-semibold tracking-tight">{t("generate.step4")}</h2>
            <dl className="grid gap-3 text-sm">
              <Row label={t("generate.step1")} value={eventType} />
              <Row label={t("generate.storyTitle")} value={title || "—"} />
              <Row label={t("generate.queryLabel")} value={query || "—"} />
              <Row label={t("generate.step2")} value={`${selectedIds.length} / ${persons?.length ?? 0}`} />
            </dl>

            <div className="flex items-center gap-2 rounded-xl border border-stone-200 bg-stone-50 p-3 text-xs dark:border-stone-800 dark:bg-stone-900/60">
              <label className="flex items-center gap-2">
                <input type="radio" checked={mode === "background"} onChange={() => setMode("background")} />
                <span>Em segundo plano (recomendado)</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="radio" checked={mode === "sync"} onChange={() => setMode("sync")} />
                <span>Aguardar resultado</span>
              </label>
            </div>
          </div>
        )}

        <div className="mt-8 flex items-center justify-between border-t border-stone-100 pt-5 dark:border-stone-800">
          <button
            onClick={() => setStep((s) => (Math.max(1, s - 1) as Step))}
            disabled={step === 1}
            className="btn btn-ghost"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>{t("common.previous")}</span>
          </button>

          {step < 4 ? (
            <button
              onClick={() => setStep((s) => (Math.min(4, s + 1) as Step))}
              disabled={!valid}
              className="btn btn-primary"
            >
              <span>{t("common.next")}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          ) : (
            <button onClick={handleGenerate} disabled={gen.isPending} className="btn btn-accent">
              {gen.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              <span>{t("generate.generate")}</span>
            </button>
          )}
        </div>
      </div>
    </>
  );
}

function Stepper({ step }: { step: Step }) {
  const { t } = useTranslation();
  const labels = [t("generate.step1"), t("generate.step2"), t("generate.step3"), t("generate.step4")];
  return (
    <ol className="flex flex-wrap items-center gap-3">
      {labels.map((label, i) => {
        const n = (i + 1) as Step;
        const active = n === step;
        const done = n < step;
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold",
                done
                  ? "bg-brand-500 text-white"
                  : active
                    ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
                    : "bg-stone-200 text-stone-500 dark:bg-stone-800 dark:text-stone-400",
              )}
            >
              {done ? <Check className="h-3.5 w-3.5" /> : n}
            </span>
            <span className={cn("text-sm", active ? "font-medium" : "text-stone-500 dark:text-stone-500")}>
              {label}
            </span>
            {i < labels.length - 1 && (
              <span aria-hidden className="h-px w-6 bg-stone-200 dark:bg-stone-800 sm:w-10" />
            )}
          </li>
        );
      })}
    </ol>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-3 border-b border-stone-100 pb-2 dark:border-stone-800">
      <dt className="w-40 shrink-0 text-xs uppercase tracking-wider text-stone-500 dark:text-stone-500">{label}</dt>
      <dd className="flex-1 text-sm">{value}</dd>
    </div>
  );
}
