import React, { useState } from 'react';

import { useI18n } from '../i18n';
import HistoryCloud from './HistoryCloud';
import HistoryOffline from './HistoryOffline';

type HistoryTab = 'offline' | 'cloud';

const History: React.FC = () => {
  const { messages } = useI18n();
  const t = messages.ui.history;
  const [tab, setTab] = useState<HistoryTab>('offline');

  return (
    <div className="flex flex-col w-full max-w-xl mx-auto space-y-8 pb-32">
      <div className="w-full text-center py-10 animate-ink">
        <h2 className="text-4xl font-black text-neutral-900 tracking-widest">{t.title}</h2>
        <p className="text-neutral-400 mt-3 font-light tracking-widest">{t.subtitle}</p>
      </div>

      <div className="flex items-center gap-2 p-1 border border-neutral-200 rounded-sm bg-white">
        <button
          onClick={() => setTab('offline')}
          className={`flex-1 py-3 text-sm tracking-widest transition ${
            tab === 'offline' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:text-neutral-900'
          }`}
        >
          {t.tabs.offline}
        </button>
        <button
          onClick={() => setTab('cloud')}
          className={`flex-1 py-3 text-sm tracking-widest transition ${
            tab === 'cloud' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:text-neutral-900'
          }`}
        >
          {t.tabs.cloud}
        </button>
      </div>

      {tab === 'offline' ? <HistoryOffline /> : <HistoryCloud />}
    </div>
  );
};

export default History;
