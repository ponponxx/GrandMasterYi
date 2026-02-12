
import { 
  AuthLoginRequest, 
  AuthLoginResponse, 
  UserProfile, 
  DivinationRequest, 
  DivinationJsonResponse,
  HistoryListResponse
} from '../types';

const BASE_URL = '/api';

export interface AdsCompleteRequest {
  provider: "admob" | "unknown";
  ad_proof: string;
}

export type AdsCompleteResponse = {
  reward_type: "silver";
  silver_granted: number;
  new_silver_balance: number;
} | {
  reward_type: "unlock";
  ad_session_token: string;
  expires_in: number;
};

class ApiService {
  private token: string | null = localStorage.getItem('auth_token');

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  logout() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers);
    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }
    if (!headers.has('Content-Type') && options.body) {
      headers.set('Content-Type', 'application/json');
    }

    const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });
    
    if (!response.ok) {
      const error = await response.text();
      // Handle specific status codes if needed
      if (response.status === 402) throw new Error('INSUFFICIENT_FUNDS');
      throw new Error(error || response.statusText);
    }

    return response.json() as Promise<T>;
  }

  async login(data: AuthLoginRequest): Promise<AuthLoginResponse> {
    const res = await this.request<AuthLoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(res.token);
    return res;
  }

  async getMe(): Promise<UserProfile> {
    return this.request<UserProfile>('/auth/me');
  }

  async performDivination(data: DivinationRequest, adSessionToken?: string): Promise<DivinationJsonResponse> {
    const headers: Record<string, string> = {};
    if (adSessionToken) {
      headers['X-Ad-Session'] = adSessionToken;
    }
    return this.request<DivinationJsonResponse>('/divination', {
      method: 'POST',
      body: JSON.stringify(data),
      headers
    });
  }

  async completeAd(data: AdsCompleteRequest): Promise<AdsCompleteResponse> {
    return this.request<AdsCompleteResponse>('/ads/complete', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getHistory(limit = 20, offset = 0): Promise<HistoryListResponse> {
    const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
    return this.request<HistoryListResponse>(`/history/list?${params.toString()}`);
  }
}

export const api = new ApiService();
