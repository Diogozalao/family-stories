import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import {
  ArrowLeft, Calendar, Check, Download, FileUp, Film, Images, Loader2, Network,
  Pencil, Plus, ScrollText, Sparkles, Timer, UploadCloud,
  User as UserIcon, Users, X,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import {
  useAddMediaToProject, useFamilies, useFamilyTree, useMedia, useProject, useProjectMedia,
  useProjectStories, useProjectVideos, useRemoveMediaFromProject,
  useUploadGedcom, useUploadPhoto,
} from "../lib/hooks";
import { downloadGedcom, extractErrorMessage } from "../lib/api";
import Photo from "../components/media/Photo";
import FamilyTree from "../components/family/FamilyTree";
import FamilyEditor from "../components/family/FamilyEditor";
import { cn, initials } from "../lib/utils";
import type { MediaFile, TimelineEvent } from "../lib/types";

type Tab = "photos" | "timeline" | "family" | "stories" | "videos";

export default function ProjectDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams();
  const projectId = id ? Number(id) : null;
  const { data: project, isLoading } = useProject(projectId);
  const [tab, setTab] = useState<Tab>("photos");

  if (isLoading) return <div className="skeleton h-64 rounded-2xl" />;
  if (!project) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-300">
        Projeto não encontrado.
      </div>
    );
  }

  return (
    <>
      <Link to="/projects" className="mb-4 inline-flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100">
        <ArrowLeft className="h-4 w-4" />
        Todos os projetos
      </Link>

      <PageHeader
        title={project.name}
        subtitle={project.description ?? "Sem descrição."}
        actions={
          <Link
            to={`/generate?project=${project.id}`}
            className="btn btn-accent"
          >
            <Sparkles className="h-4 w-4" />
            <span>Gerar história</span>
          </Link>
        }
      />

      {/* Tabs */}
      <div className="mb-6 flex flex-wrap gap-1 rounded-xl border border-stone-200 bg-white p-1 dark:border-stone-800 dark:bg-stone-900">
        <TabButton current={tab} value="photos"   onClick={setTab} icon={Images}     label={`${t("projectDetail.tabs.photos")} (${project.photos_count})`} />
        <TabButton current={tab} value="timeline" onClick={setTab} icon={Timer}      label={t("projectDetail.tabs.timeline")} />
        <TabButton current={tab} value="family"   onClick={setTab} icon={Network}    label={t("projectDetail.tabs.family")} />
        <TabButton current={tab} value="stories"  onClick={setTab} icon={ScrollText} label={`${t("projectDetail.tabs.stories")} (${project.stories_count})`} />
        <TabButton current={tab} value="videos"   onClick={setTab} icon={Film}       label={`${t("projectDetail.tabs.videos")} (${project.videos_count})`} />
      </div>

      {tab === "photos"   && <PhotosTab   projectId={project.id} />}
      {tab === "timeline" && <TimelineTab projectId={project.id} />}
      {tab === "family"   && <FamilyTab   familyLabel={project.name} />}
      {tab === "stories"  && <StoriesTab  projectId={project.id} />}
      {tab === "videos"   && <VideosTab   projectId={project.id} />}
    </>
  );
}

function TabButton({
  current, value, onClick, icon: Icon, label,
}: {
  current: Tab;
  value: Tab;
  onClick: (t: Tab) => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  const active = current === value;
  return (
    <button
      onClick={() => onClick(value)}
      className={cn(
        "flex flex-1 min-w-[120px] items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",
        active
          ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900"
          : "text-stone-600 hover:bg-stone-100 dark:text-stone-400 dark:hover:bg-stone-800",
      )}
    >
      <Icon className="h-4 w-4" />
      <span>{label}</span>
    </button>
  );
}

// ── Photos Tab ─────────────────────────────────────────────────────────────

function PhotosTab({ projectId }: { projectId: number }) {
  const { data: photos, isLoading } = useProjectMedia(projectId);
  const remove = useRemoveMediaFromProject();
  const [picker, setPicker] = useState(false);

  const items = photos ?? [];

  const handleRemove = (mediaId: number) => {
    if (!window.confirm("Remover esta foto do projeto? A foto continua na Biblioteca.")) return;
    remove.mutate({ projectId, mediaId }, {
      onSuccess: () => toast.success("Removida do projeto"),
      onError: (err) => toast.error(extractErrorMessage(err)),
    });
  };

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-stone-600 dark:text-stone-400">
          Apenas estas fotografias serão usadas quando gerares histórias dentro do projeto.
        </p>
        <button onClick={() => setPicker(true)} className="btn btn-primary">
          <Plus className="h-4 w-4" />
          <span>Adicionar fotos</span>
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton aspect-square rounded-xl" />)}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
          Ainda não há fotografias neste projeto. Clica em "Adicionar fotos" para escolher da Biblioteca.
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {items.map((m) => (
            <div key={m.id} className="group relative aspect-square overflow-hidden rounded-xl border border-stone-200 bg-stone-100 dark:border-stone-800 dark:bg-stone-900">
              <Photo
                mediaId={m.id}
                alt={m.original_filename}
                className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
              />
              <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-3 opacity-0 transition group-hover:opacity-100">
                <p className="truncate text-xs text-white/95">{m.original_filename}</p>
              </div>
              <button
                onClick={() => handleRemove(m.id)}
                className="absolute right-2 top-2 rounded-full bg-black/50 p-1.5 text-white opacity-0 backdrop-blur transition hover:bg-black/70 group-hover:opacity-100"
                aria-label="Remover do projeto"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {picker && (
        <PhotoPickerModal
          projectId={projectId}
          alreadyIn={items.map((m) => m.id)}
          onClose={() => setPicker(false)}
        />
      )}
    </>
  );
}

function PhotoPickerModal({
  projectId, alreadyIn, onClose,
}: { projectId: number; alreadyIn: number[]; onClose: () => void }) {
  const { data: all, isLoading } = useMedia();
  const add = useAddMediaToProject();
  const uploadPhoto = useUploadPhoto();
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [uploading, setUploading] = useState(false);

  // Upload brand-new photos straight into the project. They also land in
  // the global Library (so they can be reused elsewhere) and are added to
  // this project in one step.
  const onDropNew = useCallback(async (files: File[]) => {
    if (!files.length) return;
    setUploading(true);
    let ok = 0;
    for (const f of files) {
      try {
        const res: { file_id?: number } = await uploadPhoto.mutateAsync(f);
        if (res?.file_id) { await add.mutateAsync({ projectId, mediaIds: [res.file_id] }); ok++; }
      } catch (err) {
        toast.error(extractErrorMessage(err));
      }
    }
    setUploading(false);
    if (ok > 0) { toast.success(`${ok} foto(s) carregada(s) para o projeto`); onClose(); }
  }, [uploadPhoto, add, projectId, onClose]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop: onDropNew,
    accept: { "image/*": [".jpg", ".jpeg", ".png", ".webp", ".heic"] },
    noClick: true,
    noKeyboard: true,
  });

  const candidates = useMemo(
    () => (all ?? []).filter((m) => !alreadyIn.includes(m.id)),
    [all, alreadyIn],
  );

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleAdd = () => {
    if (selected.size === 0) return;
    add.mutate(
      { projectId, mediaIds: [...selected] },
      {
        onSuccess: (data: { added: number }) => {
          toast.success(`${data.added} foto(s) adicionada(s)`);
          onClose();
        },
        onError: (err) => toast.error(extractErrorMessage(err)),
      },
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/60 p-4 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="flex h-[85vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-lift dark:border-stone-800 dark:bg-stone-900"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-stone-200 p-5 dark:border-stone-800">
          <div>
            <h2 className="font-serif text-xl font-semibold tracking-tight">Adicionar fotografias ao projeto</h2>
            <p className="text-xs text-stone-500 dark:text-stone-500">
              {candidates.length} disponíveis · {selected.size} selecionadas
            </p>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {/* Option A: upload new photos straight into the project. */}
          <div
            {...getRootProps()}
            className={
              "mb-5 rounded-xl border-2 border-dashed p-4 text-center transition " +
              (isDragActive
                ? "border-brand-400 bg-brand-50/60 dark:border-brand-500 dark:bg-brand-950/30"
                : "border-stone-300 bg-white/60 dark:border-stone-700 dark:bg-stone-900/40")
            }
          >
            <input {...getInputProps()} />
            <UploadCloud className="mx-auto h-6 w-6 text-stone-400" />
            <p className="mt-2 text-xs text-stone-600 dark:text-stone-400">
              Arrasta fotos novas ou{" "}
              <button type="button" onClick={open} className="font-medium text-brand-600 hover:underline dark:text-brand-400">escolhe ficheiros</button>{" "}
              para carregar diretamente para o projeto.
            </p>
            {uploading && (
              <p className="mt-2 inline-flex items-center gap-1.5 text-xs text-stone-500">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> A carregar…
              </p>
            )}
          </div>

          {/* Option B: pick from the existing Library. */}
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-stone-400">Ou escolhe da Biblioteca</p>
          {isLoading ? (
            <div className="grid grid-cols-3 gap-3 md:grid-cols-5">
              {Array.from({ length: 10 }).map((_, i) => <div key={i} className="skeleton aspect-square rounded-xl" />)}
            </div>
          ) : candidates.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
              Não há mais fotos para adicionar. Carrega novas em <Link to="/library" className="underline">Biblioteca</Link>.
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3 md:grid-cols-5">
              {candidates.map((m: MediaFile) => {
                const isSel = selected.has(m.id);
                return (
                  <button
                    key={m.id}
                    onClick={() => toggle(m.id)}
                    className={cn(
                      "group relative aspect-square overflow-hidden rounded-xl border-2 transition",
                      isSel
                        ? "border-brand-500 ring-2 ring-brand-200 dark:ring-brand-900/40"
                        : "border-stone-200 hover:border-stone-300 dark:border-stone-800 dark:hover:border-stone-700",
                    )}
                  >
                    <Photo
                      mediaId={m.id}
                      alt={m.original_filename}
                      className="h-full w-full object-cover"
                    />
                    {isSel && (
                      <span className="absolute right-2 top-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand-500 text-white shadow-soft">
                        <Check className="h-3.5 w-3.5" />
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-stone-200 p-5 dark:border-stone-800">
          <button onClick={onClose} className="btn btn-ghost">Cancelar</button>
          <button
            onClick={handleAdd}
            disabled={selected.size === 0 || add.isPending}
            className="btn btn-primary"
          >
            {add.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            <span>Adicionar {selected.size > 0 && `(${selected.size})`}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Timeline Tab ───────────────────────────────────────────────────────────

function TimelineTab({ projectId }: { projectId: number }) {
  const { data: media, isLoading } = useProjectMedia(projectId);

  // The project timeline is built ONLY from the project's own photos —
  // each photo becomes a dated event. This keeps it scoped to the project
  // instead of mixing in the user's whole (global) timeline.
  const events: TimelineEvent[] = useMemo(
    () => (media ?? []).map((m) => ({
      id: m.id,
      event_date: m.date_taken ?? m.created_at ?? null,
      title: m.ai_setting || m.original_filename,
      description: m.ai_description ?? null,
      media_file_id: m.id,
    })),
    [media],
  );

  const grouped = useMemo(() => groupByYear(events), [events]);
  const years = Object.keys(grouped).sort((a, b) => b.localeCompare(a));

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton h-24 rounded-2xl" />
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
        Adiciona fotografias a este projeto (separador «Fotografias») para construir a linha temporal.
      </div>
    );
  }

  return (
    <div className="relative">
      <div aria-hidden className="absolute left-[11px] top-2 bottom-2 w-px bg-stone-200 dark:bg-stone-800 md:left-[91px]" />
      <div className="space-y-10">
        {years.map((y) => (
          <div key={y}>
            <div className="mb-4 flex items-center gap-3">
              <span className="relative z-10 inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand-500 text-[11px] font-semibold text-white md:ml-[78px]">
                •
              </span>
              <h3 className="font-serif text-2xl font-semibold tracking-tight">{y}</h3>
            </div>
            <div className="space-y-3">
              {grouped[y].map((ev) => (
                <TimelineRow key={ev.id} ev={ev} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TimelineRow({ ev }: { ev: TimelineEvent }) {
  const { t } = useTranslation();
  const d = ev.event_date ? new Date(ev.event_date) : null;
  const dateLabel = d
    ? d.toLocaleDateString(undefined, { day: "2-digit", month: "short" })
    : t("timeline.undated");

  return (
    <div className="flex gap-4 md:gap-6">
      <div className="hidden md:block w-20 pt-4 text-right text-xs font-medium text-stone-500 dark:text-stone-500">
        {dateLabel}
      </div>
      <div className="relative flex pt-3 md:pt-4">
        <span className="mt-1.5 inline-flex h-2.5 w-2.5 rounded-full border-2 border-white bg-brand-400 shadow-soft dark:border-stone-950" />
      </div>
      <div className="flex-1 card-soft p-4">
        <div className="flex items-center gap-2 text-xs text-stone-500 dark:text-stone-500 md:hidden">
          <Calendar className="h-3.5 w-3.5" />
          <span>{dateLabel}</span>
        </div>
        <p className="mt-0.5 font-medium">{ev.title ?? t("timeline.undated")}</p>
        {ev.description && (
          <p className="mt-1 text-sm text-stone-600 line-clamp-3 dark:text-stone-400">
            {ev.description}
          </p>
        )}
        {ev.media_file_id && (
          <div className="relative mt-3 h-48 overflow-hidden rounded-lg border border-stone-200 dark:border-stone-800">
            <Photo mediaId={ev.media_file_id} className="h-full w-full object-cover" />
          </div>
        )}
      </div>
    </div>
  );
}

function groupByYear(events: TimelineEvent[]): Record<string, TimelineEvent[]> {
  const out: Record<string, TimelineEvent[]> = {};
  for (const ev of events) {
    const y = ev.event_date ? new Date(ev.event_date).getFullYear().toString() : "—";
    (out[y] ??= []).push(ev);
  }
  for (const y of Object.keys(out)) {
    out[y].sort((a, b) => {
      const da = a.event_date ? +new Date(a.event_date) : 0;
      const db = b.event_date ? +new Date(b.event_date) : 0;
      return db - da;
    });
  }
  return out;
}

// ── Family Tab ─────────────────────────────────────────────────────────────

function FamilyTab({ familyLabel }: { familyLabel: string }) {
  const { t } = useTranslation();
  const projectLabel = familyLabel;                 // bare project group label
  const SEP = " :: ";
  const upload = useUploadGedcom();
  const { data: allFamilies } = useFamilies();

  // ``activeSub`` = the full label of the selected sub-family, or null for
  // "All" (every tree imported into this project, viewed together).
  const [activeSub, setActiveSub] = useState<string | null>(null);
  const [view, setView] = useState<"list" | "tree">("tree");
  const [editorOpen, setEditorOpen] = useState(false);

  // The list/persons of the current selection (a single sub-family, or the
  // whole project group when "All" is active).
  const { data: tree, isLoading } = useFamilyTree(
    activeSub ?? undefined,
    activeSub ? undefined : projectLabel,
  );
  const persons = tree?.persons ?? [];

  // Sub-families that belong to THIS project: the bare project label plus any
  // "<project> :: <sub>" labels. Keeps each imported GEDCOM in its own group
  // so multiple trees never merge into one.
  const subFamilies = (allFamilies ?? [])
    .filter((f): f is { label: string; count: number } =>
      !!f.label && (f.label === projectLabel || f.label.startsWith(projectLabel + SEP)));
  const subDisplay = (label: string) =>
    label === projectLabel ? t("family.unlabeled") : label.slice(projectLabel.length + SEP.length);

  // Each imported file lands in its own sub-group, named after the file, so
  // it stays isolated from the project's other trees (and other projects).
  const onDrop = useCallback(async (files: File[]) => {
    if (!files.length) return;
    const stem = files[0].name
      .replace(/\.(ged|gedcom)$/i, "").replace(/[_-]+/g, " ").trim() || "Árvore";
    const sub = `${projectLabel}${SEP}${stem}`.slice(0, 120);
    try {
      const r = await upload.mutateAsync({ file: files[0], familyLabel: sub });
      toast.success(`${r.message ?? t("common.success")}`, {
        description: subDisplay(sub),
      });
      setActiveSub(sub);
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  }, [upload, projectLabel, t]);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { "application/octet-stream": [".ged", ".gedcom"], "text/plain": [".ged", ".gedcom"] },
    maxFiles: 1,
    noClick: true,
    noKeyboard: true,
  });

  // Label used by the editor / export: the selected sub-family, or the bare
  // project label when viewing "All".
  const targetLabel = activeSub ?? projectLabel;

  return (
    <>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="chip">{t("family.persons")}: {persons.length}</span>
        <div className="flex gap-2">
          <button className="btn btn-ghost" onClick={() => setEditorOpen(true)}>
            <Pencil className="h-4 w-4" /><span>{t("family.editTree")}</span>
          </button>
          {persons.length > 0 && (
            <button
              className="btn btn-ghost"
              onClick={async () => {
                try { await downloadGedcom(targetLabel); }
                catch (err) { toast.error(extractErrorMessage(err)); }
              }}
            >
              <Download className="h-4 w-4" /><span>{t("family.exportGedcom")}</span>
            </button>
          )}
          <button className="btn btn-primary" onClick={open} disabled={upload.isPending}>
            {upload.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}
            <span>{t("family.importGedcom")}</span>
          </button>
        </div>
      </div>

      <p className="mb-4 text-xs text-stone-500 dark:text-stone-500">
        A família deste projeto («{projectLabel}») é independente da Biblioteca e dos outros projetos.
        Cada ficheiro GEDCOM importado fica no seu próprio grupo.
      </p>

      <div
        {...getRootProps()}
        className={
          "mb-4 rounded-2xl border-2 border-dashed p-5 text-center transition " +
          (isDragActive
            ? "border-brand-400 bg-brand-50/60 dark:border-brand-500 dark:bg-brand-950/30"
            : "border-stone-300 bg-white/60 dark:border-stone-700 dark:bg-stone-900/40")
        }
      >
        <input {...getInputProps()} />
        <p className="text-sm text-stone-600 dark:text-stone-400">
          {t("family.dropGedcom")}{" "}
          <button type="button" onClick={open} className="font-medium text-brand-600 hover:underline dark:text-brand-400">
            {t("library.browseFiles")}
          </button>
        </p>
      </div>

      {/* Sub-family chips — keep each imported tree separate. */}
      {subFamilies.length > 1 && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <SubChip active={activeSub === null} label={t("family.allFamilies")}
                   count={subFamilies.reduce((s, f) => s + f.count, 0)}
                   onClick={() => setActiveSub(null)} />
          {subFamilies.map((f) => (
            <SubChip key={f.label} active={activeSub === f.label}
                     label={subDisplay(f.label)} count={f.count}
                     onClick={() => setActiveSub(f.label)} />
          ))}
        </div>
      )}

      <div className="mb-4 flex w-fit gap-1 rounded-xl border border-stone-200 p-1 text-sm dark:border-stone-800">
        <button onClick={() => setView("list")} className={cn("rounded-lg px-3 py-1.5", view === "list" ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900" : "text-stone-600 dark:text-stone-400")}>{t("family.viewList")}</button>
        <button onClick={() => setView("tree")} className={cn("rounded-lg px-3 py-1.5", view === "tree" ? "bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900" : "text-stone-600 dark:text-stone-400")}>{t("family.viewTree")}</button>
      </div>

      {view === "tree" ? (
        activeSub
          ? <FamilyTree familyLabel={activeSub} />
          : <FamilyTree group={projectLabel} />
      ) : isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton h-24 rounded-2xl" />)}
        </div>
      ) : persons.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
          {t("family.noTree")} Usa «{t("family.editTree")}» para criar a árvore deste projeto.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {persons.map((p) => (
            <div key={p.id} className="card-soft p-4">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-xs font-semibold text-white">
                  {initials(p.name) || <UserIcon className="h-4 w-4" />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{p.name}</p>
                  {p.birth_date && (
                    <p className="text-xs text-stone-500 dark:text-stone-500">
                      {t("family.born", { date: p.birth_date })}
                      {p.birth_place && " " + t("family.bornAt", { place: p.birth_place })}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {editorOpen && (
        <FamilyEditor familyLabel={targetLabel} onClose={() => setEditorOpen(false)} />
      )}
    </>
  );
}

function SubChip({
  label, count, active, onClick,
}: { label: string; count: number; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition",
        active
          ? "border-brand-400 bg-brand-100 text-brand-800 dark:border-brand-700 dark:bg-brand-900/40 dark:text-brand-200"
          : "border-stone-200 bg-white text-stone-700 hover:bg-stone-50 dark:border-stone-800 dark:bg-stone-900 dark:text-stone-300",
      )}
    >
      <Users className="h-3 w-3" />
      <span className="max-w-[12rem] truncate">{label}</span>
      <span className="text-stone-500 dark:text-stone-500">· {count}</span>
    </button>
  );
}

// ── Stories Tab ────────────────────────────────────────────────────────────

function StoriesTab({ projectId }: { projectId: number }) {
  const { data, isLoading } = useProjectStories(projectId);
  const navigate = useNavigate();
  const stories = data ?? [];

  if (isLoading) return <div className="skeleton h-40 rounded-2xl" />;
  if (stories.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
        Ainda não geraste histórias neste projeto.
        <button
          onClick={() => navigate(`/generate?project=${projectId}`)}
          className="btn btn-accent mt-4"
        >
          <Sparkles className="h-4 w-4" />
          <span>Gerar primeira história</span>
        </button>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {stories.map((s) => (
        <Link
          key={s.id}
          to={`/stories/${s.id}`}
          className="card group p-5 transition hover:-translate-y-0.5 hover:shadow-lift"
        >
          <div className="flex items-center gap-2 text-xs">
            <span className="chip chip-accent">{s.event_type}</span>
            <span className="text-stone-500 dark:text-stone-500">
              {new Date(s.created_at).toLocaleDateString()}
            </span>
          </div>
          <h3 className="mt-3 font-serif text-xl font-semibold leading-snug tracking-tight line-clamp-2">
            {s.title}
          </h3>
          <p className="mt-2 text-sm text-stone-600 line-clamp-3 dark:text-stone-400">
            {(s.narrative ?? "").slice(0, 220)}…
          </p>
        </Link>
      ))}
    </div>
  );
}

// ── Videos Tab ────────────────────────────────────────────────────────────

function VideosTab({ projectId }: { projectId: number }) {
  const { data, isLoading } = useProjectVideos(projectId);
  const videos = data ?? [];

  if (isLoading) return <div className="skeleton h-40 rounded-2xl" />;
  if (videos.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
        Ainda não há vídeos neste projeto. Gera uma história primeiro e depois cria o vídeo a partir dela.
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {videos.map((v) => (
        <Link
          key={v.id}
          to="/videos"
          className="card group overflow-hidden transition hover:-translate-y-0.5 hover:shadow-lift"
        >
          <div className="aspect-video bg-gradient-to-br from-stone-800 to-stone-900" />
          <div className="p-4">
            <p className="truncate font-medium">{v.filename ?? `Vídeo #${v.id}`}</p>
            <p className="mt-1 text-xs text-stone-500 dark:text-stone-500">
              {v.status === "completed" ? "Pronto" : v.status === "processing" ? "A processar" : "Falhou"}
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}
