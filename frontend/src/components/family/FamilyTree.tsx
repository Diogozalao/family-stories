import { useCallback, useEffect } from "react";
import ReactFlow, {
  Background, Controls, Handle, MiniMap, Panel, Position,
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

  const groupCouples = (row: number[], g: number): number[] => {
    const out: number[] = [];
    const seen = new Set<number>();
    for (const id of row) {
      if (seen.has(id)) continue;
      out.push(id); seen.add(id);
      for (const sp of spousesOf.get(id) ?? []) {
        if (!seen.has(sp) && (gen.get(sp) ?? 0) === g) { out.push(sp); seen.add(sp); }
      }
    }
    return out;
  };

  const xpos = new Map<number, number>();

  gens.forEach((g, gi) => {
    const row = byGen.get(g)!;
    if (gi === 0) {
      // Top generation: lay out left-to-right, couples together.
      const ordered = groupCouples([...row].sort((a, b) => (nameOf.get(a) ?? "").localeCompare(nameOf.get(b) ?? "")), g);
      ordered.forEach((id, i) => xpos.set(id, i * X_SPACING));
    } else {
      // Each person sits at the average X of its parents → centred between
      // them (the pedigree look). Married-in people go beside their spouse.
      for (const id of row) {
        const px = (parentsOf.get(id) ?? []).map((p) => xpos.get(p)).filter((v): v is number => v != null);
        if (px.length) xpos.set(id, px.reduce((s, v) => s + v, 0) / px.length);
      }
      let maxX = Math.max(0, ...[...xpos.values()]);
      for (const id of row) {
        if (xpos.get(id) == null) {
          const sx = (spousesOf.get(id) ?? []).map((s) => xpos.get(s)).filter((v): v is number => v != null);
          if (sx.length) xpos.set(id, sx[0] + X_SPACING);
          else { maxX += X_SPACING; xpos.set(id, maxX); }
        }
      }
      // Spread out any overlaps while keeping the left-to-right order.
      const sorted = [...row].sort((a, b) => (xpos.get(a)! - xpos.get(b)!) || (nameOf.get(a) ?? "").localeCompare(nameOf.get(b) ?? ""));
      let last = -Infinity;
      for (const id of sorted) {
        const xi = Math.max(xpos.get(id)!, last + X_SPACING);
        xpos.set(id, xi);
        last = xi;
      }
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

export default function FamilyTree({ familyLabel, projectId }: { familyLabel?: string | null; projectId?: number | null }) {
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
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.2}
        nodesConnectable={false}
        nodesDraggable
      >
        <Background color="#d6d3d1" gap={20} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable nodeStrokeWidth={2} />
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
