/**
 * API contract — mirrors `backend/api/schemas/response.py`.
 * Data-structure states are a discriminated union so renderers stay type-safe.
 */

export type Language = 'python' | 'javascript' | 'typescript' | 'cpp' | 'java' | 'go' | 'rust';
export type LanguageChoice = Language | 'auto';
export type Source = 'llm' | 'static' | 'trace' | 'none';
export type NodeType = 'start' | 'process' | 'decision' | 'io' | 'end';
export type HighlightColor = 'green' | 'red' | 'yellow' | 'blue' | 'purple';

/** Primitive cell value inside a visualised structure. */
export type Scalar = string | number | boolean | null;

export interface FlowNode {
  id: string;
  type: NodeType;
  label: string;
  line: number | null;
  end_line: number | null;
  group: string;
}

export interface FlowEdge {
  source: string;
  target: string;
  label: string | null;
}

export interface Flowchart {
  nodes: FlowNode[];
  edges: FlowEdge[];
  source: Source;
}

export interface TimeComplexity {
  best: string;
  average: string;
  worst: string;
  explanation: string;
}

export interface Complexity {
  time: TimeComplexity;
  space: { complexity: string; explanation: string };
  source: Source;
}

/** Highlight target: array index, node id, map key, or [row, col]. */
export type HighlightTarget = Scalar | [number, number];

export interface Highlight {
  target: HighlightTarget;
  color: HighlightColor;
  label: string;
}

export interface TreeNode {
  id: string;
  value: Scalar;
  children: (TreeNode | null)[];
}

export interface GraphState {
  nodes: { id: string; label: string }[];
  edges: { source: string; target: string; weight: Scalar }[];
  directed: boolean;
}

interface DSBase {
  name: string;
  highlights: Highlight[];
  /** What this structure means for the problem (from the visual plan). */
  caption?: string;
}

export type DataStructureState =
  | (DSBase & { type: 'array' | 'stack' | 'queue' | 'heap'; state: { values: Scalar[] } })
  | (DSBase & { type: 'matrix'; state: { rows: Scalar[][] } })
  | (DSBase & { type: 'hash_map'; state: { entries: [Scalar, Scalar][] } })
  | (DSBase & {
      type: 'linked_list';
      /** `edges` (when present) are the live `next` pointers; otherwise nodes are chained in order. */
      state: { nodes: { id: string; value: Scalar }[]; edges?: { source: string; target: string }[]; cycle_to?: string | null };
    })
  | (DSBase & { type: 'tree'; state: { root: TreeNode | null } })
  | (DSBase & { type: 'graph'; state: GraphState });

export type DSType = DataStructureState['type'];

export interface DryRunStep {
  step: number;
  line: number | null;
  event: 'line' | 'call' | 'return' | 'exception';
  function: string;
  depth: number;
  description: string;
  variables: Record<string, string>;
  changed: string[];
  data_structure_state: DataStructureState | null;
  /** Every tracked structure at this step, in the plan's display order. */
  data_structures: DataStructureState[];
  output_so_far: string;
}

export interface CallNode {
  id: number;
  parent: number | null;
  func: string;
  args: string;
  ret: string | null;
  /** 0-based step indices of the call and its return. */
  start: number;
  end: number | null;
  /** Identical calls (same function + arguments) made before this one. */
  repeat: number;
  /** Repeat answered from a memo/cache without recursing. */
  cached: boolean;
}

export interface CallTree {
  nodes: CallNode[];
  recursive: boolean;
  repeated: number;
  cache_hits: number;
  truncated: boolean;
}

export interface VisualPlan {
  focus: string[];
  captions: Record<string, string>;
  show_recursion_tree: boolean | null;
  insight: string;
}

export interface DryRun {
  input_example: string;
  steps: DryRunStep[];
  call_tree: CallTree | null;
  plan: VisualPlan | null;
  source: Source;
  truncated: boolean;
  error: string | null;
}

export interface KeyConcept {
  concept: string;
  explanation: string;
  relevance: string;
}

/** Rich explanation fields shared by AnalysisResult and Explanation. */
export interface Teaching {
  summary: string;
  intuition: string;
  /** "Line N: …" steps. */
  approach: string[];
  why_it_works: string;
  common_mistakes: string[];
}

export interface AnalysisResult extends Teaching {
  language: Language;
  algorithm_name: string;
  data_structures_used: string[];
  complexity: Complexity;
  flowchart: Flowchart;
  dry_run: DryRun;
  key_concepts: KeyConcept[];
  edge_cases: string[];
  optimizations: string[];
  related_algorithms: string[];
  llm_used: boolean;
  warnings: string[];
}

export interface Explanation extends Teaching {
  algorithm_name: string;
  key_concepts: KeyConcept[];
  edge_cases: string[];
  optimizations: string[];
  related_algorithms: string[];
  eli5: boolean;
  llm_used: boolean;
}

export interface HealthStatus {
  status: 'ok';
  version: string;
  llm_provider: string;
  llm_model: string | null;
  llm_available: boolean;
}

export interface AnalyzeRequest {
  code: string;
  language: LanguageChoice;
  entry_call?: string | null;
  use_llm?: boolean;
  /** LeetCode mode: problem id/slug and the test case that drives the dry run. */
  problem?: string | null;
  test_input?: string[] | null;
}

/** Server-sent events emitted by `POST /api/analyze/stream`. */
export type StreamEvent =
  | { event: 'stage'; data: { stage: string; message: string } }
  | { event: 'partial' | 'result'; data: AnalysisResult }
  | { event: 'token'; data: { chars: number; phase?: 'insight' | 'dryrun' } }
  | { event: 'error'; data: { detail: string } }
  | { event: 'done'; data: Record<string, never> };

export type TabId = 'problem' | 'flowchart' | 'dryrun' | 'complexity' | 'explain';

export interface HistoryItem {
  id: string;
  createdAt: number;
  code: string;
  language: LanguageChoice;
  entryCall: string;
  title: string;
  worst: string;
}
