
import { 
  AuthLoginRequest, 
  AuthLoginResponse, 
  UserProfile, 
  DivinationRequest, 
  DivinationJsonResponse,
  HistoryListResponse,
  HistoryDetailResponse,
  TokenUsage
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

interface FakeLoginResponse {
  token: string;
}

interface PinHistoryResponse {
  ok: boolean;
}

interface DeleteHistoryResponse {
  ok: boolean;
}

export interface DivinationStreamResult {
  tokenUsage: TokenUsage | null;
}

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

  async fakeLogin(userId = `guest_${Math.random().toString(36).slice(2, 10)}`): Promise<UserProfile> {
    const res = await this.request<FakeLoginResponse>('/auth/fake_login', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    });
    this.setToken(res.token);
    return this.getMe();
  }

  async performDivination(data: DivinationRequest, adSessionToken?: string): Promise<DivinationJsonResponse> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    if (adSessionToken) {
      headers['X-Ad-Session'] = adSessionToken;
    }
    return this.request<DivinationJsonResponse>('/divination', {
      method: 'POST',
      body: JSON.stringify(data),
      headers
    });
  }

  async performDivinationStream(
    data: DivinationRequest,
    onChunk: (chunk: string) => void,
    adSessionToken?: string
  ): Promise<DivinationStreamResult> {
    const tokenUsageMarker = '[[[TOKEN_USAGE]]]';
    const headers = new Headers({
      'Accept': 'text/plain',
      'Content-Type': 'application/json',
    });

    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }
    if (adSessionToken) {
      headers.set('X-Ad-Session', adSessionToken);
    }

    const response = await fetch(`${BASE_URL}/divination`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.text();
      if (response.status === 402) {
        throw new Error('INSUFFICIENT_FUNDS');
      }
      throw new Error(error || response.statusText);
    }

    if (!response.body) {
      return { tokenUsage: null };
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let streamBuffer = '';
    let usageBuffer = '';
    let readingUsagePayload = false;

    const processIncoming = (incoming: string) => {
      if (!incoming) {
        return;
      }

      if (readingUsagePayload) {
        usageBuffer += incoming;
        return;
      }

      streamBuffer += incoming;
      const markerIndex = streamBuffer.indexOf(tokenUsageMarker);
      if (markerIndex >= 0) {
        let readable = streamBuffer.slice(0, markerIndex);
        if (readable.endsWith('\n')) {
          readable = readable.slice(0, -1);
        }
        if (readable) {
          onChunk(readable);
        }
        usageBuffer += streamBuffer.slice(markerIndex + tokenUsageMarker.length);
        streamBuffer = '';
        readingUsagePayload = true;
        return;
      }

      const tailReserve = tokenUsageMarker.length - 1;
      if (streamBuffer.length > tailReserve) {
        const emitLength = streamBuffer.length - tailReserve;
        onChunk(streamBuffer.slice(0, emitLength));
        streamBuffer = streamBuffer.slice(emitLength);
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      const chunk = decoder.decode(value, { stream: true });
      processIncoming(chunk);
    }

    processIncoming(decoder.decode());

    if (!readingUsagePayload && streamBuffer) {
      onChunk(streamBuffer);
    }

    let tokenUsage: TokenUsage | null = null;
    if (readingUsagePayload) {
      const payloadRaw = usageBuffer.trim();
      if (payloadRaw) {
        try {
          const parsed = JSON.parse(payloadRaw);
          tokenUsage = {
            input_tokens: Number(parsed?.input_tokens ?? 0),
            cached_tokens: Number(parsed?.cached_tokens ?? 0),
            thoughts_tokens: Number(parsed?.thoughts_tokens ?? 0),
            output_tokens: Number(parsed?.output_tokens ?? 0),
            total_tokens: Number(parsed?.total_tokens ?? 0),
            finish_reason: typeof parsed?.finish_reason === 'string' ? parsed.finish_reason : undefined,
            model: typeof parsed?.model === 'string' ? parsed.model : undefined,
          };
        } catch {
          tokenUsage = null;
        }
      }
    }

    return { tokenUsage };
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

  async getHistoryDetail(readingId: number): Promise<HistoryDetailResponse> {
    return this.request<HistoryDetailResponse>(`/history/detail/${readingId}`);
  }

  async pinHistory(readingId: number, isPinned: boolean): Promise<PinHistoryResponse> {
    return this.request<PinHistoryResponse>('/history/pin', {
      method: 'POST',
      body: JSON.stringify({
        reading_id: readingId,
        is_pinned: isPinned,
      }),
    });
  }

  async deleteHistory(readingId: number): Promise<DeleteHistoryResponse> {
    return this.request<DeleteHistoryResponse>('/history/delete', {
      method: 'POST',
      body: JSON.stringify({
        reading_id: readingId,
      }),
    });
  }
}

export const api = new ApiService();
