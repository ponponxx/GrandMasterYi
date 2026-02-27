
export interface AuthLoginRequest {
  provider: "google" | "apple";
  id_token: string;
}

export interface SubscriptionInfo {
  plan: "free" | "pro";
  expires_at?: string | null;
  quota: number;
  next_refill_at?: string | null;
}

export interface WalletInfo {
  gold: number;
  silver: number;
}

export interface UserProfile {
  id: string;
  email?: string | null;
  display_name?: string | null;
  subscription: SubscriptionInfo;
  wallet: WalletInfo;
  ask_count?: number;
  askCount?: number;
  history_limit: number;
}

export interface AuthLoginResponse {
  token: string;
  user: UserProfile;
}

export interface DivinationRequest {
  question: string;
  throws: (6 | 7 | 8 | 9)[];
  user_name?: string | null;
  client_context?: {
    app?: "web" | "ios" | "android";
    version?: string | null;
  } | null;
}

export interface TokenUsage {
  input_tokens: number;
  cached_tokens?: number;
  thoughts_tokens?: number;
  thoughts_token?: number;
  output_tokens: number;
  total_tokens: number;
}

export interface DivinationJsonResponse {
  reading_id?: number | null;
  hexagram_code: string;
  changing_lines: number[];
  content: string;
  saved_to_history: boolean;
  ask_count?: number | null;
  token_usage?: TokenUsage | null;
}

export interface HistoryListItem {
  reading_id: number;
  question: string;
  created_at: string;
  is_pinned: boolean;
  hexagram_code?: string;
  changing_lines?: number[];
}

export interface HistoryListResponse {
  items: HistoryListItem[];
  total: number;
}

export interface HistoryDetailResponse {
  reading_id: number;
  question: string;
  hexagram_code: string;
  changing_lines: number[];
  content: string;
  created_at: string;
  is_pinned: boolean;
}
