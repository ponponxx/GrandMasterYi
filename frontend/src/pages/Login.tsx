import React, { useState } from 'react';
import { CredentialResponse, GoogleLogin } from '@react-oauth/google';

import { LOCALE_CODES, useI18n } from '../i18n';
import { api } from '../services/api';
import { UserProfile } from '../types';

interface LoginProps {
  onLoginSuccess: (user: UserProfile) => void;
}

const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const { locale, setLocale, messages } = useI18n();
  const t = messages.ui.login;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    const idToken = credentialResponse.credential;
    if (!idToken) {
      setError(t.errors.missingIdToken);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await api.login({ provider: 'google', id_token: idToken });
      onLoginSuccess(res.user);
    } catch (err: any) {
      setError(err.message || t.errors.googleFailedDefault);
    } finally {
      setLoading(false);
    }
  };

  const handleGuestLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const guest = await api.fakeLogin();
      onLoginSuccess(guest);
    } catch (err: any) {
      setError(err.message || t.errors.guestFailedDefault);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 relative">
      <div className="absolute top-0 right-0 w-64 h-64 bg-neutral-900/5 rounded-full blur-[100px]" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-neutral-900/5 rounded-full blur-[120px]" />

      <div className="w-full max-w-sm text-center relative z-10">
        <div className="mb-12 animate-ink">
          <div className="seal-stamp text-2xl mb-6">{t.brandSeal}</div>
          <h1 className="text-4xl font-black tracking-[0.2em] text-neutral-900 mb-2">{t.title}</h1>
          <p className="text-neutral-500 font-light tracking-widest text-sm">{t.subtitle}</p>
        </div>

        {error && <div className="mb-6 p-3 border-l-4 border-red-700 bg-red-50 text-red-900 text-sm text-left">{error}</div>}

        <div className="space-y-4">
          <div className="w-full flex justify-center">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError(t.googleButtonError)}
              useOneTap={false}
              theme="filled_black"
              shape="rectangular"
              text="signin_with"
              size="large"
              width="320"
            />
          </div>

          <button
            disabled
            title={t.appleLoginTitle}
            className="w-full flex items-center justify-center gap-3 border-2 border-neutral-300 text-neutral-400 py-4 px-6 rounded-sm cursor-not-allowed opacity-70"
          >
            <span className="font-medium tracking-widest">{t.appleLoginLabel}</span>
          </button>

          <div className="py-4 flex items-center justify-center gap-4">
            <div className="h-[1px] w-8 bg-neutral-300" />
            <span className="text-xs text-neutral-400 uppercase tracking-widest">{t.orLabel}</span>
            <div className="h-[1px] w-8 bg-neutral-300" />
          </div>

          <button
            disabled={loading}
            onClick={handleGuestLogin}
            className="text-neutral-500 hover:text-neutral-900 transition text-sm underline underline-offset-8 decoration-neutral-300 hover:decoration-neutral-900"
          >
            {t.guestLoginLabel}
          </button>
        </div>

        <div className="mt-20 flex flex-col items-center gap-3">
          <div className="flex items-center justify-center gap-2">
            <label htmlFor="language-select" className="text-xs text-neutral-500 tracking-widest">
              {t.language.label}
            </label>
            <select
              id="language-select"
              value={locale}
              onChange={(e) => setLocale(e.target.value as typeof locale)}
              className="border border-neutral-300 bg-white/80 text-xs text-neutral-700 px-2 py-1 rounded-sm focus:outline-none focus:border-neutral-900"
            >
              {LOCALE_CODES.map((code) => (
                <option key={code} value={code}>
                  {t.language.options[code]}
                </option>
              ))}
            </select>
          </div>
          <div className="opacity-20 flex justify-center grayscale">
            <img
              src="https://img.icons8.com/ios-filled/50/000000/yin-yang.png"
              alt={t.yinYangAlt}
              className="w-8 h-8 rotate-infinite"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
