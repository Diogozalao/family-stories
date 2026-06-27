import { useCallback, useEffect } from "react";
import ReactFlow, {
  Background, Controls, Handle, Panel, Position,
  useEdgesState, useNodesState,
  type Edge, type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { Loader2, RotateCcw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { extractErrorMessage } from "../../lib/api";
import { useFamilyTree, useSaveTreePositions } from "../../lib/hooks";
import type { Person, TreeRelationship } from "../../lib/types";
import { cn } from "../../lib/utils";
import Photo from "../media/Photo";

// ── Custom node ─────────────────────────────────────────────────────────────

interface PersonNodeData {
  name:    string;
  years:   string;
  sex:     string | null | undefined;
  photoId: number | null | undefined;
}

function PersonNode({ data }: { data: PersonNodeData }) {
  const border =
    data.sex === "M" ? "border-sky-400 dark:border-sky-500"
    : data.sex === "F" ? "border-rose-400 dark:border-rose-500"
    : "border-stone-300 dark:border-stone-600";
  return (
    <div className={cn(
      "min-w-[120px] max-w-[180px] rounded-xl border-2 bg-white px-3 py-2 text-center shadow-soft dark:bg-stone-900",
      border,
    )}>
      <Handle type="target" position={Position.Top}    className="!opacity-0" />
      <Handle type="source" position={Position.Bottom} className="!opacity-0" />
      <Handle type="target" position={Position.Left}  id="l" className="!opacity-0" />
      <Handle type="source" position={Position.Right} id="r" className="!opacity-0" />
      {data.photoId != null && (
        <div className="relative mx-auto mb-1.5 h-12 w-12 overflow-hidden rounded-full border border-stone-200 dark:border-stone-700">
          <Photo mediaId={data.photoId} alt={data.name} className="h-full w-full object-cover" />
        </div>
      )}
      <div className="truncate text-xs font-medium text-stone-900 dark:text-stone-100">{data.name}</div>
      {data.years && <div className="text-[10px] text-stone-500 dark:text-stone-500">{data.years}</div>}
    </div>
  );
}

const nodeTypes = { person: PersonNode };

// ── Layout (generational + barycenter ordering) ───────────────────────────────

const X_SPACING = 210;
const Y_SPACING = 150;

function pushMap<K, V>(m: Map<K, V[]>, k: K, v: V) {
  const a = m.get(k);
  if (a) a.push(v); else m.set(k, [v]);
}

function yearsLabel(p: Person): string {
  const b = p.birth_date?.slice(0, 4);
  const d = p.death_date?.slice(0, 4);
  if (b && d) return `${b}–${d}`;
  if (b) return b;
  if (d) return `–${d}`;
  return "";
}

function computeLayout(persons: Person[], rels: TreeRelationship[]): Map<number, { x: number; y: number }> {
  const ids = persons.map((p) => p.id);
  const idset = new Set(ids);
  const parentsOf = new Map<number, number[]>();
  const spousesOf = new Map<number, number[]>();
  for (const r of rels) {
    if (!idset.has(r.from) || !idset.has(r.to)) continue;
    if (r.kind === "cônjuge") { pushMap(spousesOf, r.from, r.to); pushMap(spousesOf, r.to, r.from); }
    else { pushMap(parentsOf, r.to, r.from); }   // r.from is parent of r.to
  }

  // Generation = longest parent-chain depth (relaxation). Oldest ancestors
  // (no parents) sit at generation 0 (top); descendants grow downwards.
  const gen = new Map<number, number>(ids.map((id) => [id, 0]));
  for (let i = 0; i < ids.length + 2; i++) {
    let changed = false;
    for (const r of rels) {
      if (r.kind === "cônjuge" || !idset.has(r.from) || !idset.has(r.to)) continue;
      const want = (gen.get(r.from) ?? 0) + 1;
      if ((gen.get(r.to) ?? 0) < want) { gen.set(r.to, want); changed = true; }
    }
    if (!changed) break;
  }
  // Pull a married-in spouse (e.g. someone with no parents in the tree) down
  // onto the same generation as the person they married.
  for (let i = 0; i < 4; i++) {
    for (const r of rels) {
      if (r.kind !== "cônjuge" || !idset.has(r.from) || !idset.has(r.to)) continue;
      const g = Math.max(gen.get(r.from) ?? 0, gen.get(r.to) ?? 0);
      gen.set(r.from, g); gen.set(r.to, g);
    }
  }

  const nameOf = new Map(persons.map((p) => [p.id, p.name]));
  const byGen = new Map<number, number[]>();
  for (const id of ids) pushMap(byGen, gen.get(id) ?? 0, id);
  const gens = [...byGen.keys()].sort((a, b) => a - b);

  // ── Unit-based layout (proper genealogy rules) ──────────────────────────
  // A "unit" is a couple [husband, wife] or a single person. Members of a
  // unit are ALWAYS laid out consecutively, so spouses sit side by side with
  // nobody between them; a child unit is centred under its parents' unit.
  const UNIT_GAP = X_SPACING * 0.4;     // extra breathing room between units

  const unitsFor = (row: number[], g: number): number[][] => {
    const seen = new Set<number>();
    const units: number[][] = [];
    for (const id of row) {
      if (seen.has(id)) continue;
      seen.add(id);
      const unit = [id];
      for (const sp of spousesOf.get(id) ?? []) {
        if (!seen.has(sp) && (gen.get(sp) ?? 0) === g) { unit.push(sp); seen.add(sp); }
      }
      units.push(unit);
    }
    return units;
  };

  const xpos = new Map<number, number>();

  // Lay ``units`` left-to-right; each unit aims for ``targets[i]`` (its centre)
  // but never overlaps the previous one. Members stay adjacent within a unit.
  const placeUnits = (units: number[][], targets: (number | null)[]) => {
    let rightEdge = -Infinity;          // x of the rightmost node placed so far
    units.forEach((unit, i) => {
      const span = (unit.length - 1) * X_SPACING;
      // First unit may start at 0; later ones clear the previous unit + a gap.
      const minStart = rightEdge === -Infinity ? 0 : rightEdge + X_SPACING + UNIT_GAP;
      let start = targets[i] != null ? (targets[i] as number) - span / 2 : minStart;
      if (start < minStart) start = minStart;
      unit.forEach((id, k) => xpos.set(id, start + k * X_SPACING));
      rightEdge = start + span;
    });
  };

  gens.forEach((g, gi) => {
    const row = byGen.get(g)!;
    if (gi === 0) {
      // Top generation: order couples by name, lay out left-to-right.
      const ordered = [...row].sort((a, b) => (nameOf.get(a) ?? "").localeCompare(nameOf.get(b) ?? ""));
      const units = unitsFor(ordered, g);
      placeUnits(units, units.map(() => null));
    } else {
      // Each unit is centred under the average X of its members' parents
      // (the pedigree look). Units with no placed parents go to the right.
      const parentBary = (id: number): number => {
        const px = (parentsOf.get(id) ?? []).map((p) => xpos.get(p)).filter((v): v is number => v != null);
        return px.length ? px.reduce((s, v) => s + v, 0) / px.length : NaN;
      };
      // Order each couple's two members by which side their parents are on, so
      // the two "child→parents" lines don't cross over each other.
      const units = unitsFor(row, g).map((unit) => {
        if (unit.length !== 2) return unit;
        return [...unit].sort((a, b) => {
          const pa = parentBary(a), pb = parentBary(b);
          if (isNaN(pa) && isNaN(pb)) return 0;
          if (isNaN(pa)) return 1;          // married-in (no parents) → outside
          if (isNaN(pb)) return -1;
          return pa - pb;                   // left-parented spouse on the left
        });
      });
      const targets = units.map((unit) => {
        const px = unit.flatMap((m) => parentsOf.get(m) ?? [])
          .map((p) => xpos.get(p)).filter((v): v is number => v != null);
        return px.length ? px.reduce((s, v) => s + v, 0) / px.length : null;
      });
      // Order units by their target (children follow their parents' order).
      const order = units.map((_, i) => i).sort((a, b) => {
        const ta = targets[a], tb = targets[b];
        if (ta == null && tb == null) return a - b;
        if (ta == null) return 1;
        if (tb == null) return -1;
        return ta - tb;
      });
      placeUnits(order.map((i) => units[i]), order.map((i) => targets[i]));
    }
  });

  const pos = new Map<number, { x: number; y: number }>();
  for (const id of ids) pos.set(id, { x: xpos.get(id) ?? 0, y: (gen.get(id) ?? 0) * Y_SPACING });
  return pos;
}

function buildGraph(persons: Person[], rels: TreeRelationship[]): { nodes: Node<PersonNodeData>[]; edges: Edge[] } {
  const idset = new Set(persons.map((p) => p.id));
  const pos = computeLayout(persons, rels);

  const nodes: Node<PersonNodeData>[] = persons.map((p) => ({
    id: String(p.id),
    type: "person",
    // Use the hand-dragged position when the user saved one; otherwise the
    // automatic pedigree layout.
    position: (p.tree_x != null && p.tree_y != null)
      ? { x: p.tree_x, y: p.tree_y }
      : (pos.get(p.id) ?? { x: 0, y: 0 }),
    data: { name: p.name, years: yearsLabel(p), sex: p.sex, photoId: p.photo_media_id },
  }));

  const edges: Edge[] = rels.flatMap((r): Edge[] => {
    if (!idset.has(r.from) || !idset.has(r.to)) return [];
    if (r.kind === "cônjuge") {
      return [{
        id: `r${r.id}`, source: String(r.from), target: String(r.to),
        sourceHandle: "r", targetHandle: "l", type: "straight",
        style: { stroke: "#f43f5e", strokeDasharray: "4 3" },
      }];
    }
    return [{
      id: `r${r.id}`, source: String(r.from), target: String(r.to),
      type: "smoothstep", style: { stroke: "#a8a29e" },
    }];
  });

  return { nodes, edges };
}

// ── Component ───────────────────────────────────────────────────────────────

export default function FamilyTree({ familyLabel, projectId, onPersonClick }: {
  familyLabel?: string | null;
  projectId?: number | null;
  /** Click a node → edit that person (id). */
  onPersonClick?: (id: number) => void;
}) {
  const { t } = useTranslation();
  const { data, isLoading } = useFamilyTree(familyLabel ?? undefined, projectId ?? undefined);

  // ``useNodesState`` keeps the nodes editable so the user can DRAG them
  // freely; we re-seed the auto-layout whenever the underlying data changes.
  const [nodes, setNodes, onNodesChange] = useNodesState<PersonNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const qc = useQueryClient();
  const savePos = useSaveTreePositions();

  useEffect(() => {
    const { nodes: n, edges: e } = buildGraph(data?.persons ?? [], data?.relationships ?? []);
    setNodes(n);
    setEdges(e);
  }, [data, setNodes, setEdges]);

  // Persist a node's position when the user finishes dragging it.
  const onNodeDragStop = useCallback((_evt: React.MouseEvent, node: Node) => {
    savePos.mutate(
      { positions: [{ id: Number(node.id), x: node.position.x, y: node.position.y }] },
      { onError: (err) => toast.error(extractErrorMessage(err)) },
    );
  }, [savePos]);

  // Clear all saved positions → fall back to the automatic layout.
  const resetLayout = () => {
    const persons = data?.persons ?? [];
    if (!persons.length) return;
    savePos.mutate(
      { positions: persons.map((p) => ({ id: p.id, x: null, y: null })) },
      { onSuccess: () => qc.invalidateQueries({ queryKey: ["tree"] }) },
    );
  };

  if (isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center rounded-2xl border border-stone-200 dark:border-stone-800">
        <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
      </div>
    );
  }

  if ((data?.persons ?? []).length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-stone-300 bg-white/50 p-12 text-center text-sm text-stone-500 dark:border-stone-700 dark:bg-stone-900/40">
        {t("family.noTree")}
      </div>
    );
  }

  return (
    <div className="h-[68vh] w-full overflow-hidden rounded-2xl border border-stone-200 bg-stone-50 dark:border-stone-800 dark:bg-stone-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStop={onNodeDragStop}
        onNodeClick={(_e, node) => onPersonClick?.(Number(node.id))}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.2}
        nodesConnectable={false}
        nodesDraggable
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#d6d3d1" gap={20} />
        <Controls showInteractive={false} />
        <Panel position="top-right">
          <button
            onClick={resetLayout}
            className="inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white/90 px-2.5 py-1.5 text-xs font-medium text-stone-700 shadow-soft backdrop-blur hover:bg-white dark:border-stone-700 dark:bg-stone-900/90 dark:text-stone-200"
            title={t("family.resetLayout")}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            {t("family.resetLayout")}
          </button>
        </Panel>
      </ReactFlow>
    </div>
  );
}
