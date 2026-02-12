
import React, { useState } from 'react';
import { api } from '../services/api';
import { UserProfile } from '../types';

interface LoginProps {
  onLoginSuccess: (user: UserProfile) => void;
}

const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (provider: 'google' | 'apple' | 'guest') => {
    setLoading(true);
    setError(null);
    try {
      if (provider === 'guest') {
        const mockGuest: UserProfile = {
          id: 'guest_' + Math.random().toString(36).substr(2, 9),
          display_name: '訪客',
          subscription: { plan: 'free', quota: 3 },
          wallet: { gold: 0, silver: 10 },
          history_limit: 10
        };
        onLoginSuccess(mockGuest);
      } else {
        const res = await api.login({ provider, id_token: 'mock_token' });
        onLoginSuccess(res.user);
      }
    } catch (err: any) {
      setError(err.message || '登錄失敗');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative">
      {/* Background Ink Wash Effect */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-neutral-900/5 rounded-full blur-[100px]"></div>
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-neutral-900/5 rounded-full blur-[120px]"></div>

      <div className="w-full max-w-sm text-center relative z-10">
        <div className="mb-12 animate-ink">
          <div className="seal-stamp text-2xl mb-6">萬象易理</div>
          <h1 className="text-4xl font-black tracking-[0.2em] text-neutral-900 mb-2">周易占卜</h1>
          <p className="text-neutral-500 font-light tracking-widest text-sm">Seek the balance of Yin and Yang</p>
        </div>

        {error && <div className="mb-6 p-3 border-l-4 border-red-700 bg-red-50 text-red-900 text-sm text-left">{error}</div>}

        <div className="space-y-4">
          <button 
            disabled={loading}
            onClick={() => handleLogin('google')}
            className="w-full flex items-center justify-center gap-3 bg-neutral-900 text-white py-4 px-6 rounded-sm transition hover:bg-black active:scale-[0.98] disabled:opacity-50 shadow-lg shadow-black/10"
          >
            <span className="font-medium tracking-widest">Google 帳號登入</span>
          </button>

          <button 
            disabled={loading}
            onClick={() => handleLogin('apple')}
            className="w-full flex items-center justify-center gap-3 border-2 border-neutral-900 text-neutral-900 py-4 px-6 rounded-sm transition hover:bg-neutral-100 active:scale-[0.98] disabled:opacity-50"
          >
            <span className="font-medium tracking-widest">Apple 帳號登入</span>
          </button>

          <div className="py-4 flex items-center justify-center gap-4">
            <div className="h-[1px] w-8 bg-neutral-300"></div>
            <span className="text-xs text-neutral-400 uppercase tracking-widest">或</span>
            <div className="h-[1px] w-8 bg-neutral-300"></div>
          </div>

          <button 
            disabled={loading}
            onClick={() => handleLogin('guest')}
            className="text-neutral-500 hover:text-neutral-900 transition text-sm underline underline-offset-8 decoration-neutral-300 hover:decoration-neutral-900"
          >
            以訪客身份進入
          </button>
        </div>

        <div className="mt-20 opacity-20 flex justify-center grayscale">
           <img src="https://img.icons8.com/ios-filled/50/000000/yin-yang.png" alt="Yin Yang" className="w-8 h-8 rotate-infinite" />
        </div>
      </div>
    </div>
  );
};

export default Login;
