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
};

export type ThreadSummary = {
  id: string;
  title: string;
  updatedAt: string;
};

export type ProfileSnapshot = {
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
