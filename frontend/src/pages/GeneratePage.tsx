import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, Check, FolderKanban, Loader2, Sparkles } from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import {
  useGenerateNarrative, useIndexFacts, usePersons, useProject, useStories,
  useTemplates,
} from "../lib/hooks";
import { extractErrorMessage, isLostResponse } from "../lib/api";
import type { Story } from "../lib/types";
import { useGenerateDraft } from "../store/generateDraft";
import { cn, initials } from "../lib/utils";

type Step = 1 | 2 | 3 | 4;

export default function GeneratePage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [params] = useSearchParams();
  const projectId = params.get("project") ? Number(params.get("project")) : null;
  const { data: project } = useProject(projectId);

  const { data: templates } = useTemplates();
  const { data: persons } = usePersons();
  const { data: stories } = useStories();
  const gen = useGenerateNarrative();
  const index = useIndexFacts();

  // Wizard state lives in a persisted store so navigating away (and back)
  // doesn't wipe what the user has filled in.
  const {
    step, eventType, title, query, customTone, customStructure,
    selectedIds, mode, patch, reset,
  } = useGenerateDraft();
  const setStep = (s: Step) => patch({ step: s });

  const isCustom = eventType === "custom";

  // ── People grouped into family "folders" ─────────────────────────────────
  // The picker shows ONE family at a time. In a project it defaults to that
  // project's family, but you can switch folders to pull in someone from
  // another family if you want.
  const SEM_FAMILIA = "Sem família";
  const families = useMemo(() => {
    const set = new Set<string>();
    for (const p of persons ?? []) set.add(p.family_label || SEM_FAMILIA);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [persons]);
  const [activeFamily, setActiveFamily] = useState<string | null>(null);
  useEffect(() => {
    if (activeFamily !== null || families.length === 0) return;
    setActiveFamily(
      project?.name && families.includes(project.name) ? project.name : families[0],
    );
  }, [families, project?.name, activeFamily]);
  const familyPersons = useMemo(
    () => (persons ?? []).filter((p) => (p.family_label || SEM_FAMILIA) === activeFamily),
    [persons, activeFamily],
  );

  const valid = useMemo(() => {
    if (step === 1) return !!eventType;
    if (step === 3) {
      const baseOk = title.trim().length >= 3 && query.trim().length >= 5;
      // Custom theme requires at least a tone — structure is optional.
      if (isCustom) return baseOk && customTone.trim().length >= 3;
      return baseOk;
    }
    return true;
  }, [step, eventType, title, query, isCustom, customTone]);

  const togglePerson = (id: number) => {
    patch({
      selectedIds: selectedIds.includes(id)
        ? selectedIds.filter((x) => x !== id)
        : [...selectedIds, id],
    });
  };

  // Navigate to the freshly created story (where the "make video" button is)
  // so the user is immediately ready to produce the documentary.
  const goToStory = (id: number) => {
    reset();
    navigate(projectId ? `/projects/${projectId}` : `/stories/${id}`);
  };

  const handleGenerate = () => {
    // Snapshot which stories already exist so we can spot the new one if the
    // response is lost to a cold-start drop (see onError below).
    const beforeIds = new Set((stories ?? []).map((s) => s.id));

    gen.mutate(
      {
        title: title.trim(),
        event_type: eventType,
        query: query.trim(),
        person_ids: selectedIds,
        project_id: projectId ?? undefined,
        custom_tone:      isCustom ? customTone.trim() || undefined      : undefined,
        custom_structure: isCustom ? customStructure.trim() || undefined : undefined,
        // i18n.language is "pt" or "en" — the M3 LLM writes in that
        // language and the M4 TTS later picks the matching voice.
        language:         i18n.language === "en" ? "en" : "pt",
        mode,
      },
      {
        onSuccess: (data: any) => {
          // Sync result (or a background request that the cloud downgraded
          // to sync because there's no Celery worker) gives us a Story.
          if (data?.id) {
            goToStory(data.id);
            return;
          }
          // A real queued task (only when a worker exists): poll via Tasks.
          if (data?.task_id) {
            reset();
            toast.success(t("videos.processing"));
            navigate(projectId ? `/projects/${projectId}` : "/tasks");
            return;
          }
          reset();
          navigate("/stories");
        },
        onError: async (err) => {
          // Cold-start lost response: the story was very likely created on
          // the server even though the reply never came back. Give it a
          // moment, refetch, and if a new story appeared, open it — instead
          // of a scary "Network Error". We never re-submit (that would
          // create a duplicate story).
          if (isLostResponse(err)) {
            await new Promise((r) => setTimeout(r, 3000));
            await qc.refetchQueries({ queryKey: ["stories"] });
            const fresh = qc.getQueryData<Story[]>(["stories"]) ?? [];
            const created = fresh.find((s) => !beforeIds.has(s.id));
            if (created) {
              toast.success(t("generate.recovered"));
              goToStory(created.id);
              return;
            }
            toast.error(t("generate.coldRetry"));
            return;
          }
          toast.error(extractErrorMessage(err));
        },
      },
    );
  };

  return (
    <>
      <PageHeader
        title={t("generate.title")}
        subtitle={
          project
            ? `Esta história será criada dentro do projeto "${project.name}" e usará apenas as fotografias adicionadas a ele.`
            : t("generate.subtitle")
        }
        actions={
          <>
            {project && (
              <span className="chip chip-accent">
                <FolderKanban className="h-3.5 w-3.5" />
                {project.name}
              </span>
            )}
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
          </>
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
                  onClick={() => patch({ eventType: tpl.id })}
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
            <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
              {t("generate.selectPeople")}
              {selectedIds.length > 0 && <span className="ml-1 text-brand-600 dark:text-brand-400">· {selectedIds.length} selecionada(s)</span>}
            </p>

            {/* Family "folders" — pick which family to choose people from. */}
            {families.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {families.map((f) => (
                  <button
                    key={f}
                    onClick={() => setActiveFamily(f)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition",
                      activeFamily === f
                        ? "border-brand-400 bg-brand-100 text-brand-800 dark:border-brand-700 dark:bg-brand-900/40 dark:text-brand-200"
                        : "border-stone-200 bg-white text-stone-700 hover:bg-stone-50 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300",
                    )}
                  >
                    <FolderKanban className="h-3.5 w-3.5" />
                    {f}
                  </button>
                ))}
              </div>
            )}

            <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {familyPersons.map((p) => {
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
                onChange={(e) => patch({ title: e.target.value })}
                placeholder={t("generate.storyTitlePlaceholder")}
              />
            </div>
            <div>
              <label className="label">{t("generate.queryLabel")}</label>
              <textarea
                className="input min-h-[140px] resize-y"
                value={query}
                onChange={(e) => patch({ query: e.target.value })}
                placeholder={t("generate.queryPlaceholder")}
              />
              <p className="mt-1.5 text-xs text-stone-500 dark:text-stone-500">
                Esta descrição passa a ser a <strong>intenção principal</strong> do prompt enviado ao LLM.
                Sê o mais específico possível: ângulo, emoção, período, eventos.
              </p>
            </div>

            {isCustom && (
              <>
                <div>
                  <label className="label">Tom da narrativa</label>
                  <input
                    className="input"
                    value={customTone}
                    onChange={(e) => patch({ customTone: e.target.value })}
                    placeholder="ex.: melancólico e sarcástico, sombrio com humor seco, formal e crítico"
                  />
                  <p className="mt-1.5 text-xs text-stone-500 dark:text-stone-500">
                    Obrigatório no tema personalizado — é o que distingue este texto dos outros.
                  </p>
                </div>
                <div>
                  <label className="label">Estrutura (opcional)</label>
                  <input
                    className="input"
                    value={customStructure}
                    onChange={(e) => patch({ customStructure: e.target.value })}
                    placeholder="ex.: cena inicial → conflito → desabafo final"
                  />
                </div>
              </>
            )}
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
                <input type="radio" checked={mode === "background"} onChange={() => patch({ mode: "background" })} />
                <span>Em segundo plano (recomendado)</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="radio" checked={mode === "sync"} onChange={() => patch({ mode: "sync" })} />
                <span>Aguardar resultado</span>
              </label>
            </div>
          </div>
        )}

        <div className="mt-8 flex items-center justify-between border-t border-stone-100 pt-5 dark:border-stone-800">
          <button
            onClick={() => setStep(Math.max(1, step - 1) as Step)}
            disabled={step === 1}
            className="btn btn-ghost"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>{t("common.previous")}</span>
          </button>

          {step < 4 ? (
            <button
              onClick={() => setStep(Math.min(4, step + 1) as Step)}
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
