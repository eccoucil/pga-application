"use client";

import { useCallback, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Connection,
  addEdge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Info, ChevronDown, ChevronUp } from "lucide-react";
import type { KnowledgeGraph } from "@/types/assessment";

interface ContextNodesGraphProps {
  knowledgeGraph: KnowledgeGraph;
}

/** Hub/category nodes: Organization, Industry — yellow oval, larger */
const HUB_NODE_TYPES = new Set(["Organization", "Industry"]);

const MAX_HUB_LABEL = 50;
const MAX_ENTITY_LABEL = 25;

function truncateLabel(label: string, maxLen: number): string {
  if (!label || label.length <= maxLen) return label;
  return label.slice(0, maxLen).trim() + "…";
}

/** Hub node: yellow oval, black text; handles on all 4 sides for radial layout */
function HubNode({ data }: { data: { label: string; node_type: string } }) {
  const raw = data.label || data.node_type;
  const display = truncateLabel(raw, MAX_HUB_LABEL);
  return (
    <div
      className="flex items-center justify-center px-6 py-3 rounded-[9999px] border border-amber-600/30 shadow-sm"
      style={{
        backgroundColor: "#facc15",
        minWidth: 140,
        maxWidth: 220,
      }}
    >
      <Handle type="target" position={Position.Top} id="t-top" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="target" position={Position.Left} id="t-left" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="target" position={Position.Bottom} id="t-bottom" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="target" position={Position.Right} id="t-right" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <span
        className="text-black text-sm font-semibold text-center leading-tight px-1"
        title={raw !== display ? raw : undefined}
      >
        {display}
      </span>
      <Handle type="source" position={Position.Top} id="s-top" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="source" position={Position.Right} id="s-right" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="source" position={Position.Bottom} id="s-bottom" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="source" position={Position.Left} id="s-left" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
    </div>
  );
}

/** Entity node: teal circle, black text; handles on all 4 sides for radial layout */
function EntityNode({ data }: { data: { label: string; node_type: string } }) {
  const raw = data.label || data.node_type;
  const display = truncateLabel(raw, MAX_ENTITY_LABEL);
  return (
    <div
      className="flex items-center justify-center rounded-full border border-teal-700/30 shadow-sm w-[72px] h-[72px]"
      style={{ backgroundColor: "#14b8a6" }}
    >
      <Handle type="target" position={Position.Top} id="t-top" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="target" position={Position.Left} id="t-left" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="target" position={Position.Bottom} id="t-bottom" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="target" position={Position.Right} id="t-right" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <span
        className="text-black text-xs font-medium text-center leading-tight px-1.5 line-clamp-2"
        title={raw !== display ? raw : undefined}
      >
        {display}
      </span>
      <Handle type="source" position={Position.Top} id="s-top" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="source" position={Position.Right} id="s-right" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="source" position={Position.Bottom} id="s-bottom" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
      <Handle type="source" position={Position.Left} id="s-left" className="!w-2 !h-2 !border-2 !border-gray-400 !bg-white" />
    </div>
  );
}

const nodeTypes = {
  hub: HubNode,
  entity: EntityNode,
  default: EntityNode,
};

const CENTER_X = 400;
const CENTER_Y = 300;
const RING_1_RADIUS = 250;
const RING_2_RADIUS = 450;

export function ContextNodesGraph({ knowledgeGraph }: ContextNodesGraphProps) {
  const [showInfo, setShowInfo] = useState(true);
  // Radial layout: hub at center, children on concentric rings
  const initialNodes = useMemo<Node[]>(() => {
    if (!knowledgeGraph?.nodes || knowledgeGraph.nodes.length === 0) return [];

    const edges = knowledgeGraph.edges ?? [];
    const nodeIds = new Set(knowledgeGraph.nodes.map((n) => n.id));
    const targetsBySource = new Map<string, string[]>();
    const sourcesByTarget = new Map<string, string[]>();
    for (const e of edges) {
      if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) continue;
      if (!targetsBySource.has(e.source)) targetsBySource.set(e.source, []);
      targetsBySource.get(e.source)!.push(e.target);
      if (!sourcesByTarget.has(e.target)) sourcesByTarget.set(e.target, []);
      sourcesByTarget.get(e.target)!.push(e.source);
    }

    // BFS to assign level (0 = hub/roots, 1 = direct children, 2+ = deeper)
    const levelByNode = new Map<string, number>();
    const queue: { id: string; level: number }[] = [];
    for (const n of knowledgeGraph.nodes) {
      const hasIncoming = sourcesByTarget.has(n.id);
      if (!hasIncoming) {
        levelByNode.set(n.id, 0);
        queue.push({ id: n.id, level: 0 });
      }
    }
    if (queue.length === 0) {
      const first = knowledgeGraph.nodes[0];
      levelByNode.set(first.id, 0);
      queue.push({ id: first.id, level: 0 });
    }
    while (queue.length > 0) {
      const { id, level } = queue.shift()!;
      const targets = targetsBySource.get(id) ?? [];
      for (const t of targets) {
        const existing = levelByNode.get(t);
        const nextLevel = level + 1;
        if (existing == null || nextLevel < existing) {
          levelByNode.set(t, nextLevel);
          queue.push({ id: t, level: nextLevel });
        }
      }
    }
    for (const n of knowledgeGraph.nodes) {
      if (levelByNode.has(n.id)) continue;
      levelByNode.set(n.id, 1);
    }

    // Group by level
    const byLevel = new Map<number, typeof knowledgeGraph.nodes>();
    for (const n of knowledgeGraph.nodes) {
      const l = levelByNode.get(n.id) ?? 0;
      if (!byLevel.has(l)) byLevel.set(l, []);
      byLevel.get(l)!.push(n);
    }
    const maxLevel = Math.max(...byLevel.keys(), 0);

    const nodes: Node[] = [];

    // Level 0: hub node(s) at center — stack vertically if multiple roots
    const hubNodes = byLevel.get(0) ?? [];
    for (let i = 0; i < hubNodes.length; i++) {
      const node = hubNodes[i];
      const isHub =
        node.data?.node_type && HUB_NODE_TYPES.has(node.data.node_type);
      nodes.push({
        id: node.id,
        type: isHub ? "hub" : "entity",
        position: { x: CENTER_X, y: CENTER_Y + i * 80 },
        data: node.data,
      });
    }

    // Level 1+: arrange on concentric rings
    for (let level = 1; level <= maxLevel; level++) {
      const levelNodes = byLevel.get(level) ?? [];
      const radius = level === 1 ? RING_1_RADIUS : RING_1_RADIUS + (level - 1) * (RING_2_RADIUS - RING_1_RADIUS);
      const count = levelNodes.length;
      const angleStep = (2 * Math.PI) / count;
      // Start from top (-π/2) so first node is above center
      const startAngle = -Math.PI / 2;

      for (let i = 0; i < count; i++) {
        const node = levelNodes[i];
        const angle = startAngle + i * angleStep;
        const x = CENTER_X + radius * Math.cos(angle);
        const y = CENTER_Y + radius * Math.sin(angle);
        const isHub =
          node.data?.node_type && HUB_NODE_TYPES.has(node.data.node_type);
        nodes.push({
          id: node.id,
          type: isHub ? "hub" : "entity",
          position: { x, y },
          data: node.data,
        });
      }
    }

    return nodes;
  }, [knowledgeGraph]);

  // Thin grey edges (reference style: many thin grey lines, no arrows)
  const initialEdges = useMemo<Edge[]>(() => {
    if (!knowledgeGraph?.edges || knowledgeGraph.edges.length === 0) return [];

    const nodeIds = new Set(knowledgeGraph.nodes.map((n) => n.id));
    return knowledgeGraph.edges
      .filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        style: {
          stroke: "#9ca3af",
          strokeWidth: 1,
          opacity: 1,
        },
      }));
  }, [knowledgeGraph]);

  const [reactFlowNodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [reactFlowEdges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  if (!knowledgeGraph?.nodes || knowledgeGraph.nodes.length === 0) {
    return (
      <div className="h-[500px] flex items-center justify-center bg-white rounded-lg border border-gray-200">
        <p className="text-gray-500">No knowledge graph data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Info Banner */}
      <div className="bg-slate-900/40 border border-cyan-500/20 rounded-lg overflow-hidden">
        <button
          onClick={() => setShowInfo(!showInfo)}
          className="w-full flex items-start gap-3 p-4 hover:bg-slate-800/40 transition-colors text-left"
        >
          <Info className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white mb-1">
              Knowledge Graph Overview
            </p>
            {showInfo && (
              <p className="text-xs text-slate-300 leading-relaxed">
                This graph visualizes the relationships between your organization, digital assets, policies, and documents discovered during the assessment. Nodes are arranged radially with the organization at the center, showing how different compliance entities connect and relate to each other.
              </p>
            )}
          </div>
          <div className="flex-shrink-0 mt-0.5">
            {showInfo ? (
              <ChevronUp className="w-4 h-4 text-slate-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-400" />
            )}
          </div>
        </button>

        {/* Legend */}
        {showInfo && (
          <div className="px-4 pb-4 pt-2 border-t border-slate-700/50 space-y-3">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Node Types
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Hub Node */}
              <div className="flex items-center gap-3 p-2 bg-slate-800/30 rounded border border-slate-700/50">
                <div
                  className="w-12 h-8 rounded-full border border-amber-600/30 flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: "#facc15" }}
                >
                  <span className="text-black text-xs font-bold">Org</span>
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-white">
                    Organization / Hub
                  </p>
                  <p className="text-xs text-slate-400">
                    Central node representing your organization
                  </p>
                </div>
              </div>

              {/* Entity Node */}
              <div className="flex items-center gap-3 p-2 bg-slate-800/30 rounded border border-slate-700/50">
                <div
                  className="w-8 h-8 rounded-full border border-teal-700/30 flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: "#14b8a6" }}
                >
                  <span className="text-black text-xs font-bold">A</span>
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-white">
                    Entity Node
                  </p>
                  <p className="text-xs text-slate-400">
                    Assets, policies, documents, and other related items
                  </p>
                </div>
              </div>
            </div>

            {/* Connections */}
            <div className="pt-2">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                Connections
              </p>
              <p className="text-xs text-slate-300 flex items-center gap-2">
                <span
                  className="inline-block w-4 h-px"
                  style={{ backgroundColor: "#9ca3af" }}
                />
                Lines show relationships and dependencies between entities
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ReactFlow Graph */}
      <div className="h-[500px] w-full bg-white rounded-lg border border-gray-200 overflow-hidden">
        <ReactFlow
          nodes={reactFlowNodes}
          edges={reactFlowEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          className="bg-white"
          defaultViewport={{ x: 0, y: 0, zoom: 0.7 }}
          nodesDraggable={true}
          nodesConnectable={false}
          edgesFocusable={true}
          defaultEdgeOptions={{
            animated: false,
            style: { stroke: "#9ca3af", strokeWidth: 1, opacity: 1 },
          }}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#e5e7eb" gap={16} size={1} />
          <Controls
            className="bg-white border border-gray-200 rounded-lg shadow-sm"
            style={{ color: "#374151" }}
          />
          <MiniMap
            className="bg-white border border-gray-200 rounded-lg shadow-sm"
            nodeColor={(node) => (node.type === "hub" ? "#facc15" : "#14b8a6")}
            maskColor="rgba(0, 0, 0, 0.08)"
          />
        </ReactFlow>
      </div>
    </div>
  );
}
