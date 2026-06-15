import { useMemo } from "react";
import ReactFlow, {
  Background, Controls, Handle, MiniMap, Position,
  type Edge, type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useFamilyTree } from "../../lib/hooks";
import type { Person, TreeRelationship } from "../../lib/types";
import { cn } from "../../lib/utils";

// ── Custom node ─────────────────────────────────────────────────────────────

interface PersonNodeData {
  name:  string;
  years: string;
  sex:   string | null | undefined;
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
      <div className="truncate text-xs font-medium text-stone-900 dark:text-stone-100">{data.name}</div>
      {data.years && <div className="text-[10px] text-stone-500 dark:text-stone-500">{data.years}</div>}
    </div>
  );
}

const nodeTypes = { person: PersonNode };

// ── Layout (generational grid) ────────────────────────────────────────────────

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
  const spousesOf = new Map<number, number[]>();
  for (const r of rels) {
    if (!idset.has(r.from) || !idset.has(r.to)) continue;
    if (r.kind === "cônjuge") { pushMap(spousesOf, r.from, r.to); pushMap(spousesOf, r.to, r.from); }
  }

  // Generation = longest parent-chain depth (relaxation).
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
  // Pull spouses onto the same generation.
  for (let i = 0; i < 3; i++) {
    for (const r of rels) {
      if (r.kind !== "cônjuge" || !idset.has(r.from) || !idset.has(r.to)) continue;
      const g = Math.max(gen.get(r.from) ?? 0, gen.get(r.to) ?? 0);
      gen.set(r.from, g); gen.set(r.to, g);
    }
  }

  const nameOf = new Map(persons.map((p) => [p.id, p.name]));
  const byGen = new Map<number, number[]>();
  for (const id of ids) pushMap(byGen, gen.get(id) ?? 0, id);

  const pos = new Map<number, { x: number; y: number }>();
  for (const g of [...byGen.keys()].sort((a, b) => a - b)) {
    const row = byGen.get(g)!.sort((a, b) => (nameOf.get(a) ?? "").localeCompare(nameOf.get(b) ?? ""));
    // Reorder so spouses sit next to each other.
    const ordered: number[] = [];
    const seen = new Set<number>();
    for (const id of row) {
      if (seen.has(id)) continue;
      ordered.push(id); seen.add(id);
      for (const sp of spousesOf.get(id) ?? []) {
        if (!seen.has(sp) && (gen.get(sp) ?? 0) === g) { ordered.push(sp); seen.add(sp); }
      }
    }
    ordered.forEach((id, i) => pos.set(id, { x: i * X_SPACING, y: g * Y_SPACING }));
  }
  return pos;
}

// ── Component ───────────────────────────────────────────────────────────────

export default function FamilyTree({ familyLabel }: { familyLabel?: string | null }) {
  const { t } = useTranslation();
  const { data, isLoading } = useFamilyTree(familyLabel ?? undefined);

  const { nodes, edges } = useMemo(() => {
    const persons = data?.persons ?? [];
    const rels    = data?.relationships ?? [];
    const idset   = new Set(persons.map((p) => p.id));
    const pos     = computeLayout(persons, rels);

    const nodes: Node<PersonNodeData>[] = persons.map((p) => ({
      id: String(p.id),
      type: "person",
      position: pos.get(p.id) ?? { x: 0, y: 0 },
      data: { name: p.name, years: yearsLabel(p), sex: p.sex },
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
  }, [data]);

  if (isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center rounded-2xl border border-stone-200 dark:border-stone-800">
        <Loader2 className="h-6 w-6 animate-spin text-stone-400" />
      </div>
    );
  }

  if (nodes.length === 0) {
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
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.2}
        nodesConnectable={false}
        nodesDraggable
      >
        <Background color="#d6d3d1" gap={20} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable nodeStrokeWidth={2} />
      </ReactFlow>
    </div>
  );
}
