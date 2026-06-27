import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Check, ImagePlus, Loader2, Pencil, Search, Trash2, Upload, X } from "lucide-react";

import Photo from "../media/Photo";
import PhotoViewer from "../media/PhotoViewer";
import {
  useMedia, useProjectMedia, useSetMediaPersons, useUpdatePerson, useUploadPhoto,
} from "../../lib/hooks";
import { extractErrorMessage } from "../../lib/api";
import type { MediaFile, Person } from "../../lib/types";

/**
 * Per-person photo/document gallery.
 *
 * A person's photos are the media tagged with them (``media.person_ids``).
 * From here the user manages that set directly — attaching photos/documents
 * (e.g. their portrait *and* a birth certificate) or detaching them — which
 * is the inverse of tagging "who appears" from the photo side. The same set
 * is what the generation wizard later offers when this person is chosen.
 *
 * When opened inside a project, ``projectId`` scopes the pool to that
 * project's photos (both the person's photos and the ones offered to add),
 * matching the project's isolated view; in the global Family page it spans
 * the whole library.
 */
export default function PersonGallery({
  personId, personName, projectId = null, person, onClose,
}: {
  personId: number;
  personName: string;
  projectId?: number | null;
  /** Full person data — enables the inline "edit details" form. */
  person?: Person | null;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  // Both hooks must run (hooks can't be conditional); the project one is
  // disabled when there's no projectId, so it's a no-op in the global view.
  const { data: allMedia }     = useMedia();
  const { data: projectMedia } = useProjectMedia(projectId);
  const media = projectId != null ? projectMedia : allMedia;
  const setPersons   = useSetMediaPersons();
  const updatePerson = useUpdatePerson();
  const uploadPhoto  = useUploadPhoto();

  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState(false);
  const [query, setQuery] = useState("");
  const [viewerIdx, setViewerIdx] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);

  // Editable detail fields, seeded from the person.
  const [form, setForm] = useState({
    name:        person?.name ?? personName,
    birth_date:  person?.birth_date?.slice(0, 10) ?? "",
    death_date:  person?.death_date?.slice(0, 10) ?? "",
    birth_place: person?.birth_place ?? "",
    notes:       person?.notes ?? "",
  });
  const patchForm = (p: Partial<typeof form>) => setForm((f) => ({ ...f, ...p }));

  const saveDetails = async () => {
    try {
      await updatePerson.mutateAsync({
        id: personId,
        name:        form.name.trim() || personName,
        birth_date:  form.birth_date || null,
        death_date:  form.death_date || null,
        birth_place: form.birth_place.trim() || null,
        notes:       form.notes.trim() || null,
      });
      toast.success(t("common.success"));
      setEditing(false);
    } catch (err) {
      toast.error(extractErrorMessage(err));
    }
  };

  // Upload a photo straight from the PC and make it this person's profile
  // picture (and tag them in it). No need to go via the Library/Photos.
  const onPickLocal = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true);
    try {
      const res: { file_id?: number } = await uploadPhoto.mutateAsync(
        projectId != null ? { file, projectId } : file,
      );
      if (res?.file_id) {
        await setPersons.mutateAsync({ id: res.file_id, person_ids: [personId] });
        await updatePerson.mutateAsync({ id: personId, photo_media_id: res.file_id });
        toast.success(t("person.profileSet"));
      }
    } catch (err) {
      toast.error(extractErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const photos = useMemo(
    () => (media ?? []).filter((m) => m.media_type !== "video"),
    [media],
  );
  const mine   = useMemo(() => photos.filter((m) => (m.person_ids ?? []).includes(personId)), [photos, personId]);
  const others = useMemo(() => {
    const q = query.trim().toLowerCase();
    return photos
      .filter((m) => !(m.person_ids ?? []).includes(personId))
      .filter((m) => !q || (m.original_filename + " " + (m.ai_description ?? "")).toLowerCase().includes(q));
  }, [photos, personId, query]);

  const setTag = (m: MediaFile, attach: boolean) => {
    const cur = m.person_ids ?? [];
    const next = attach ? [...cur, personId] : cur.filter((x) => x !== personId);
    setPersons.mutate(
      { id: m.id, person_ids: next },
      { onError: (err) => toast.error(extractErrorMessage(err)) },
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/80 p-4 backdrop-blur" onClick={onClose}>
      <div
        className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-stone-200 bg-white shadow-lift dark:border-stone-800 dark:bg-stone-900"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 border-b border-stone-100 p-5 dark:border-stone-800">
          <div>
            <h2 className="font-serif text-xl font-semibold tracking-tight">{personName}</h2>
            <p className="mt-0.5 text-sm text-stone-600 dark:text-stone-400">
              {t("person.galleryLead")}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button onClick={() => { setEditing((v) => !v); setAdding(false); }} className="btn btn-ghost">
              <Pencil className="h-4 w-4" /><span>{t("person.editDetails")}</span>
            </button>
            <label className="btn btn-ghost cursor-pointer" title={t("person.fromPCHint")}>
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
              <span>{t("person.fromPC")}</span>
              <input type="file" accept="image/*" className="hidden"
                     onChange={(e) => onPickLocal(e.target.files?.[0])} />
            </label>
            <button onClick={() => { setAdding((v) => !v); setEditing(false); }} className={adding ? "btn btn-ghost" : "btn btn-primary"}>
              {adding ? <X className="h-4 w-4" /> : <ImagePlus className="h-4 w-4" />}
              <span>{adding ? t("common.close") : t("person.addPhotos")}</span>
            </button>
            <button onClick={onClose} className="rounded-lg p-1.5 text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-800" aria-label={t("common.close")}>
              <X className="h-5 w-5" />
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {editing ? (
            <div className="mx-auto max-w-lg space-y-4">
              <div>
                <label className="label">{t("person.fieldName")}</label>
                <input className="input" value={form.name} onChange={(e) => patchForm({ name: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">{t("person.fieldBirth")}</label>
                  <input type="date" className="input" value={form.birth_date} onChange={(e) => patchForm({ birth_date: e.target.value })} />
                </div>
                <div>
                  <label className="label">{t("person.fieldDeath")}</label>
                  <input type="date" className="input" value={form.death_date} onChange={(e) => patchForm({ death_date: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="label">{t("person.fieldPlace")}</label>
                <input className="input" value={form.birth_place} onChange={(e) => patchForm({ birth_place: e.target.value })} />
              </div>
              <div>
                <label className="label">{t("person.fieldNotes")}</label>
                <textarea className="input min-h-[120px] resize-y" value={form.notes} onChange={(e) => patchForm({ notes: e.target.value })} />
              </div>
              <div className="flex justify-end gap-2">
                <button className="btn btn-ghost" onClick={() => setEditing(false)}>{t("common.cancel")}</button>
                <button className="btn btn-primary" onClick={saveDetails} disabled={updatePerson.isPending}>
                  {updatePerson.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                  {t("common.save")}
                </button>
              </div>
            </div>
          ) : adding ? (
            <>
              <div className="relative mb-4 max-w-md">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t("common.search")}
                  className="input pl-9"
                />
              </div>
              {others.length === 0 ? (
                <p className="py-10 text-center text-sm text-stone-500">{t("person.noneToAdd")}</p>
              ) : (
                <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
                  {others.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setTag(m, true)}
                      className="group relative aspect-square overflow-hidden rounded-lg border border-stone-200 transition hover:border-brand-400 dark:border-stone-800"
                      title={m.ai_description || m.original_filename}
                    >
                      <Photo mediaId={m.id} alt={m.original_filename} className="h-full w-full object-cover" />
                      <span className="absolute inset-0 flex items-center justify-center bg-black/0 text-white opacity-0 transition group-hover:bg-black/40 group-hover:opacity-100">
                        <ImagePlus className="h-6 w-6" />
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </>
          ) : mine.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-stone-300 bg-stone-50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
              {t("person.empty")}
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-5">
              {mine.map((m, idx) => (
                <div key={m.id} className="group relative aspect-square overflow-hidden rounded-lg border border-stone-200 bg-stone-100 dark:border-stone-800 dark:bg-stone-900">
                  <Photo
                    mediaId={m.id}
                    alt={m.original_filename}
                    onClick={() => setViewerIdx(idx)}
                    className="h-full w-full cursor-zoom-in object-cover transition group-hover:scale-105"
                  />
                  <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-2 opacity-0 transition group-hover:opacity-100">
                    <p className="line-clamp-2 text-[10px] leading-snug text-white/95">
                      {m.ai_description || m.original_filename}
                    </p>
                  </div>
                  <button
                    onClick={() => setTag(m, false)}
                    className="absolute right-1.5 top-1.5 inline-flex h-7 w-7 items-center justify-center rounded-full bg-stone-950/55 text-white opacity-0 transition hover:bg-rose-600 group-hover:opacity-100"
                    aria-label={t("person.remove")}
                    title={t("person.remove")}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <footer className="flex items-center justify-between gap-2 border-t border-stone-100 px-5 py-3 text-xs text-stone-500 dark:border-stone-800 dark:text-stone-500">
          <span className="inline-flex items-center gap-1.5">
            <Check className="h-3.5 w-3.5 text-emerald-500" />
            {t("person.count", { count: mine.length })}
          </span>
          {setPersons.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        </footer>
      </div>

      {viewerIdx !== null && mine[viewerIdx] && (
        <PhotoViewer items={mine} index={viewerIdx} onChange={setViewerIdx}
                     onClose={() => setViewerIdx(null)} projectId={projectId} />
      )}
    </div>
  );
}
