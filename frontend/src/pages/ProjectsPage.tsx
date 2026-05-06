import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  Film, FolderPlus, Images, Loader2, Plus, ScrollText, Trash2,
} from "lucide-react";
import PageHeader from "../components/ui/PageHeader";
import { useCreateProject, useDeleteProject, useProjects } from "../lib/hooks";
import { extractErrorMessage } from "../lib/api";
import { photoUrl } from "../lib/photo";
import type { Project } from "../lib/types";

export default function ProjectsPage() {
  const { data, isLoading } = useProjects();
  const [open, setOpen] = useState(false);
  const projects = data ?? [];

  return (
    <>
      <PageHeader
        title="Projetos"
        subtitle="Espaços de trabalho que agrupam fotos, histórias e vídeos relacionados."
        actions={
          <button onClick={() => setOpen(true)} className="btn btn-accent">
            <Plus className="h-4 w-4" />
            <span>Novo projeto</span>
          </button>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton h-56 rounded-2xl" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <EmptyState onNew={() => setOpen(true)} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => <ProjectCard key={p.id} project={p} />)}
        </div>
      )}

      {open && <CreateProjectModal onClose={() => setOpen(false)} />}
    </>
  );
}

function ProjectCard({ project }: { project: Project }) {
  const del = useDeleteProject();

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Apagar o projeto "${project.name}"? As fotografias na Biblioteca permanecem.`)) return;
    del.mutate(project.id, {
      onSuccess: () => toast.success("Projeto apagado"),
      onError: (err) => toast.error(extractErrorMessage(err)),
    });
  };

  return (
    <Link
      to={`/projects/${project.id}`}
      className="group relative flex flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-soft transition hover:-translate-y-0.5 hover:shadow-lift dark:border-stone-800 dark:bg-stone-900"
    >
      <div className="relative aspect-[16/10] overflow-hidden bg-gradient-to-br from-stone-200 to-amber-100 dark:from-stone-800 dark:to-stone-900">
        {project.cover_media_id ? (
          <img
            src={photoUrl(project.cover_media_id)}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-stone-400 dark:text-stone-600">
            <FolderPlus className="h-10 w-10" />
          </div>
        )}
        <button
          onClick={handleDelete}
          disabled={del.isPending}
          className="absolute right-2 top-2 rounded-full bg-black/50 p-1.5 text-white opacity-0 backdrop-blur transition hover:bg-black/70 group-hover:opacity-100"
          title="Apagar projeto"
          aria-label="Apagar"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex flex-1 flex-col p-5">
        <h3 className="font-serif text-xl font-semibold leading-snug tracking-tight">{project.name}</h3>
        {project.description && (
          <p className="mt-2 text-sm text-stone-600 line-clamp-2 dark:text-stone-400">{project.description}</p>
        )}
        <div className="mt-auto flex items-center gap-3 pt-4 text-xs text-stone-500 dark:text-stone-500">
          <span className="inline-flex items-center gap-1"><Images   className="h-3.5 w-3.5" />{project.photos_count}</span>
          <span className="inline-flex items-center gap-1"><ScrollText className="h-3.5 w-3.5" />{project.stories_count}</span>
          <span className="inline-flex items-center gap-1"><Film     className="h-3.5 w-3.5" />{project.videos_count}</span>
          <span className="ml-auto">{new Date(project.updated_at).toLocaleDateString()}</span>
        </div>
      </div>
    </Link>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div className="rounded-3xl border border-dashed border-stone-300 bg-white/50 p-14 text-center dark:border-stone-700 dark:bg-stone-900/40">
      <FolderPlus className="mx-auto h-10 w-10 text-stone-400" />
      <h3 className="mt-4 font-serif text-2xl font-semibold tracking-tight">Ainda não tens projetos</h3>
      <p className="mx-auto mt-2 max-w-md text-sm text-stone-600 dark:text-stone-400">
        Cria um projeto para agrupar fotografias relacionadas — por exemplo
        "Casamento dos avós" ou "Viagem ao Algarve 1985" — e gera histórias
        focadas só nessas memórias.
      </p>
      <button onClick={onNew} className="btn btn-accent mt-6">
        <Plus className="h-4 w-4" />
        <span>Criar o primeiro projeto</span>
      </button>
    </div>
  );
}

function CreateProjectModal({ onClose }: { onClose: () => void }) {
  const create = useCreateProject();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim().length === 0) return;
    create.mutate(
      { name: name.trim(), description: description.trim() || undefined },
      {
        onSuccess: (project) => {
          toast.success(`Projeto "${project.name}" criado`);
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
        className="w-full max-w-lg rounded-2xl border border-stone-200 bg-white p-6 shadow-lift animate-scale-in dark:border-stone-800 dark:bg-stone-900"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-serif text-2xl font-semibold tracking-tight">Novo projeto</h2>
        <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">
          Dá-lhe um nome curto e descritivo. Podes adicionar fotos e histórias depois.
        </p>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="label" htmlFor="proj-name">Nome</label>
            <input
              id="proj-name"
              autoFocus
              required
              maxLength={120}
              className="input"
              placeholder="ex.: Casamento dos avós"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="proj-desc">Descrição (opcional)</label>
            <textarea
              id="proj-desc"
              className="input min-h-[80px] resize-y"
              placeholder="Algumas frases sobre o que este projeto vai conter."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn btn-ghost">Cancelar</button>
            <button
              type="submit"
              disabled={create.isPending || name.trim().length === 0}
              className="btn btn-primary"
            >
              {create.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              <span>Criar</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
