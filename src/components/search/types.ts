export type Role = "user" | "assistant";

export type SourceItem = {
  label: string;
  href?: string;
};

export type SourceCitation = {
  label: string;
  href?: string;
  sourceId?: string;
  verificationStatus?: string;
  pageType?: string;
};

export type RoadmapStep = {
  step: number;
  product: string;
  reason: string;
  url?: string;
};

export type Roadmap = {
  title: string;
  profile_summary?: string[];
  steps?: RoadmapStep[];
};

export type NavigatorSummary = {
  title: string;
  summary: string;
  why_this_path?: string[];
  next_move?: string;
};

export type ComparisonRow = {
  item: string;
  best_for: string;
  why: string;
};

export type BulletGroup = {
  title: string;
  items: string[];
};

export type DecisionSummary = {
  primary_recommendation?: {
    product?: string;
    display_product?: string;
    why?: string[];
    confidence?: "low" | "medium" | "high" | string;
  };
  secondary_recommendations?: Array<{
    product?: string;
    display_product?: string;
    why?: string[];
  }>;
  current_lane?: string;
  next_best_action?: {
    label?: string;
    href?: string;
    reason?: string;
  };
  scored_products?: Array<{
    product?: string;
    display_product?: string;
    score?: number;
    reasons?: string[];
  }>;
  signals?: string[];
};

export type UiModule = {
  module_type:
    | "profile_card"
    | "recommendation_card"
    | "comparison_table"
    | "live_context"
    | "next_action"
    | "verification_box"
    | string;
  visible?: boolean;
  priority?: number;
  payload?: Record<string, unknown>;
};

export type AnswerStyle =
  | "brief"
  | "standard"
  | "overview"
  | "compare"
  | "roadmap"
  | "detailed";

export type ResponsePresentation = {
  answer_style?: AnswerStyle | string;
  show_visual_panel?: boolean;
  show_recommended_products?: boolean;
  show_navigator_summary?: boolean;
  show_roadmap?: boolean;
  show_chips?: boolean;
  show_bullet_groups?: boolean;
  show_comparison_table?: boolean;
  module_policy?: string[];
};

export type VisualHint =
  | "ecosystem_map"
  | "trust_signal"
  | "markets_tools"
  | "portfolio_view"
  | "learning_lane"
  | "events_network";

export type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  createdAt: string;
  sources?: SourceItem[];
  sourceCitations?: SourceCitation[];
  recommendedProducts?: string[];
  verificationNotes?: string[];
  roadmap?: Roadmap;
  chips?: string[];
  navigatorSummary?: NavigatorSummary | null;
  visualHint?: string | null;
  answerStyle?: AnswerStyle | string | null;
  presentation?: ResponsePresentation | null;
  decision?: DecisionSummary | null;
  comparisonRows?: ComparisonRow[];
  bulletGroups?: BulletGroup[];
  uiModules?: UiModule[];
  htmlSnippets?: string[];
};

export type ThreadSummary = {
  id: string;
  title: string;
  updatedAt: string;
};

export type ProfileSnapshot = {
  name?: string;
  intent?: string;
  sophistication?: string;
  goal?: string;
  profession?: string;
  interests?: string[];
  existing_products?: string[];
  age_range?: string;
  onboarding_complete?: boolean;
};

export type JourneyEvent = {
  timestamp?: string;
  route?: string;
  user_message?: string;
  assistant_message?: string;
  recommendations?: string[];
  recommended_products?: string[];
  source_citations?: SourceCitation[];
  verification_notes?: string[];
  navigator_summary?: NavigatorSummary | null;
  roadmap?: Roadmap | null;
  chips?: string[];
  visual_hint?: string | null;
  answer_style?: string | null;
  presentation?: ResponsePresentation | null;
  decision?: DecisionSummary | null;
  comparison_rows?: ComparisonRow[];
  bullet_groups?: BulletGroup[];
  ui_modules?: UiModule[];
  profile_snapshot?: ProfileSnapshot;
};

export type SessionDocument = {
  session_id: string;
  title: string;
  profile: ProfileSnapshot;
  onboarding_complete: boolean;
  questions_asked: string[];
  messages: Array<{ role: string; content: string }>;
  journey_history: JourneyEvent[];
  recommendations: string[];
  recommended_products: string[];
  response_type?: string | null;
  updated_at?: string | null;
};

export type MarketSnapshotItem = {
  symbol: string;
  label: string;
  price: number;
  change: number;
  changePct: number;
  sparkline: number[];
  etRoute: string;
  href: string;
};

export type MarketSnapshotLink = {
  label: string;
  href: string;
  note: string;
};

export type MarketSnapshot = {
  asOf: string;
  sourceLabel: string;
  items: MarketSnapshotItem[];
  etLinks: MarketSnapshotLink[];
};
