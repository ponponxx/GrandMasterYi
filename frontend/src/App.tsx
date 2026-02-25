import React, { useEffect, useState } from 'react';

import { useI18n } from './i18n';
import Achievements from './pages/Achievements';
import Divination from './pages/Divination';
import History from './pages/History';
import Login from './pages/Login';
import Shop from './pages/Shop';
import { api } from './services/api';
import { UserProfile } from './types';

type Tab = 'main' | 'shop' | 'history' | 'achievements';

const App: React.FC = () => {
  const { messages } = useI18n();
  const t = messages.ui.app;
  const [user, setUser] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('main');
  const [initializing, setInitializing] = useState(true);
  const tabMeta: Record<Tab, { label: string; icon: string }> = {
    main: t.tabs.main,
    shop: t.tabs.shop,
    history: t.tabs.history,
    achievements: t.tabs.achievements,
  };

  useEffect(() => {
    const init = async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          const profile = await api.getMe();
          setUser(profile);
        } catch {
          api.logout();
        }
      }
      setInitializing(false);
    };
    init();
  }, []);

  useEffect(() => {
    if (!user) {
      return;
    }

    let cancelled = false;
    const syncProfile = async () => {
      try {
        const profile = await api.getMe();
        if (!cancelled) {
          setUser(profile);
        }
      } catch {
        // Keep current cached profile if refresh fails temporarily.
      }
    };

    syncProfile();
    return () => {
      cancelled = true;
    };
  }, [activeTab]);

  if (initializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f2efe6]">
        <div className="w-10 h-10 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return <Login onLoginSuccess={setUser} />;
  }

  return (
    <div className="min-h-screen relative pb-20">
      <header className="fixed top-0 left-0 right-0 z-40 bg-white/40 backdrop-blur-md border-b border-neutral-100">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="text-2xl">{t.brandIcon}</div>
            <h1 className="font-black tracking-[0.2em] text-neutral-900 text-sm">{t.brandTitle}</h1>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-4">
              <div className="flex flex-col items-end">
                <span className="text-[9px] text-neutral-400 font-bold tracking-widest uppercase">{t.wallet.gold}</span>
                <span className="text-sm font-bold text-neutral-900">{user.wallet.gold}</span>
              </div>
              <div className="w-px h-6 bg-neutral-200" />
              <div className="flex flex-col items-end">
                <span className="text-[9px] text-neutral-400 font-bold tracking-widest uppercase">{t.wallet.silver}</span>
                <span className="text-sm font-bold text-neutral-900">{user.wallet.silver}</span>
              </div>
            </div>
            <button
              onClick={() => {
                api.logout();
                setUser(null);
              }}
              className="text-neutral-400 hover:text-red-700 transition-colors"
              title={t.logoutTitle}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main className="pt-20 px-6 min-h-screen animate-ink">
        <section className={activeTab === 'main' ? 'block' : 'hidden'}>
          <Divination user={user} onUserUpdate={setUser} />
        </section>
        <section className={activeTab === 'shop' ? 'block' : 'hidden'}>
          <Shop user={user} />
        </section>
        <section className={activeTab === 'history' ? 'block' : 'hidden'}>
          <History />
        </section>
        <section className={activeTab === 'achievements' ? 'block' : 'hidden'}>
          <Achievements />
        </section>
      </main>

      <nav className="fixed bottom-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-xl border-t border-neutral-100 safe-area-inset-bottom">
        <div className="max-w-xl mx-auto flex justify-between items-center px-8 h-20">
          <NavButton
            active={activeTab === 'main'}
            onClick={() => setActiveTab('main')}
            label={tabMeta.main.label}
            icon={tabMeta.main.icon}
          />
          <NavButton
            active={activeTab === 'shop'}
            onClick={() => setActiveTab('shop')}
            label={tabMeta.shop.label}
            icon={tabMeta.shop.icon}
          />
          <NavButton
            active={activeTab === 'history'}
            onClick={() => setActiveTab('history')}
            label={tabMeta.history.label}
            icon={tabMeta.history.icon}
          />
          <NavButton
            active={activeTab === 'achievements'}
            onClick={() => setActiveTab('achievements')}
            label={tabMeta.achievements.label}
            icon={tabMeta.achievements.icon}
          />
        </div>
      </nav>
    </div>
  );
};

interface NavButtonProps {
  active: boolean;
  onClick: () => void;
  label: string;
  icon: string;
}

const NavButton: React.FC<NavButtonProps> = ({ active, onClick, label, icon }) => (
  <button
    onClick={onClick}
    className={`flex flex-col items-center gap-1 transition-all duration-500 relative ${
      active ? 'text-neutral-900 scale-110' : 'text-neutral-400 hover:text-neutral-600'
    }`}
  >
    <div className={`text-2xl transition-all duration-300 ${active ? 'opacity-100' : 'opacity-60 grayscale'}`}>{icon}</div>
    <span
      className={`text-[10px] font-bold tracking-[0.2em] transition-all duration-300 ${
        active ? 'opacity-100 mt-1' : 'opacity-0 h-0'
      }`}
    >
      {label}
    </span>
    {active && <div className="absolute -bottom-2 w-1 h-1 bg-red-700 rounded-full animate-pulse" />}
  </button>
);

export default App;
