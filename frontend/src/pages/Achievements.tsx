import React, { useCallback, useEffect, useMemo, useState } from 'react';

import { useI18n } from '../i18n';
import { lookupHexagramByCodeAndLines } from '../services/ichingLocal';
import { api } from '../services/api';
import { listOfflineReadings, OFFLINE_HISTORY_UPDATED_EVENT } from '../services/offlineHistoryDb';
import { HistoryListItem, UserProfile } from '../types';

const pictureModules = import.meta.glob('../../assets/picture/*.png', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

const pictureMap = Object.entries(pictureModules).reduce<Record<number, string>>((acc, [path, url]) => {
  const match = path.match(/\/(\d+)\.png$/);
  if (match) {
    acc[Number(match[1])] = url;
  }
  return acc;
}, {});

type HexagramPreview = {
  id: number;
  title: string;
  judgment: string;
};

interface AchievementsProps {
  user: UserProfile;
}

const fillTemplate = (template: string, vars: Record<string, string | number>) => {
  let out = template;
  Object.entries(vars).forEach(([key, value]) => {
    out = out.replace(`{${key}}`, String(value));
  });
  return out;
};

const getAskCount = (user: UserProfile) => {
  if (typeof user.askCount === 'number') {
    return user.askCount;
  }
  if (typeof user.ask_count === 'number') {
    return user.ask_count;
  }
  return 0;
};

const Achievements: React.FC<AchievementsProps> = ({ user }) => {
  const { messages } = useI18n();
  const t = messages.ui.achievements;
  const [discovered, setDiscovered] = useState<Record<number, HexagramPreview>>({});
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const loadCloudHistory = useCallback(async (): Promise<HistoryListItem[]> => {
    const limit = 200;
    let offset = 0;
    let total = Number.POSITIVE_INFINITY;
    const all: HistoryListItem[] = [];

    while (all.length < total) {
      const res = await api.getHistory(limit, offset);
      all.push(...res.items);
      total = Number(res.total || 0);
      if (res.items.length === 0) {
        break;
      }
      offset += res.items.length;
    }

    return all;
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    const map = new Map<number, HexagramPreview>();

    try {
      const offlineReadings = await listOfflineReadings(2000);
      offlineReadings.forEach((item) => {
        const id = Number(item.hexagram_id);
        if (!Number.isInteger(id) || id < 1 || id > 64 || map.has(id)) {
          return;
        }

        const title = `${fillTemplate(t.hexagramTitleTemplate, { id })} ${item.display_name || ''}`.trim();
        const judgment = item.trigram_title ? `${item.trigram_title} ${item.judgment}` : item.judgment;
        map.set(id, { id, title, judgment });
      });
    } catch (error) {
      console.error(error);
    }

    try {
      const cloudReadings = await loadCloudHistory();
      for (const item of cloudReadings) {
        const hexagramCode = String(item.hexagram_code || '').trim();
        if (!/^[01]{6}$/.test(hexagramCode)) {
          continue;
        }
        try {
          const context = await lookupHexagramByCodeAndLines(hexagramCode, item.changing_lines || []);
          if (map.has(context.hexagramId)) {
            continue;
          }
          const title = `${fillTemplate(t.hexagramTitleTemplate, { id: context.hexagramId })} ${context.displayName || ''}`.trim();
          const judgment = context.trigramTitle ? `${context.trigramTitle} ${context.judgment}` : context.judgment;
          map.set(context.hexagramId, { id: context.hexagramId, title, judgment });
        } catch (error) {
          console.error(error);
        }
      }
    } catch (error) {
      console.error(error);
    }

    setDiscovered(Object.fromEntries(map.entries()));
    setLoading(false);
  }, [loadCloudHistory, t.hexagramTitleTemplate]);

  useEffect(() => {
    const handler = () => {
      refresh();
    };
    window.addEventListener(OFFLINE_HISTORY_UPDATED_EVENT, handler);
    return () => window.removeEventListener(OFFLINE_HISTORY_UPDATED_EVENT, handler);
  }, [refresh]);

  useEffect(() => {
    refresh();
  }, [refresh, user.askCount, user.ask_count]);

  const discoveredCount = useMemo(() => Object.keys(discovered).length, [discovered]);
  const readingCount = useMemo(() => getAskCount(user), [user]);
  const stage = useMemo(() => Math.max(1, Math.ceil(discoveredCount / 8)), [discoveredCount]);
  const selected = selectedId ? discovered[selectedId] : null;
  const selectedImage = selectedId ? pictureMap[selectedId] : '';

  return (
    <div className="flex flex-col items-center w-full max-w-4xl mx-auto space-y-12 pb-32">
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-2xl bg-white border-2 border-neutral-900 p-6 md:p-8 rounded-sm shadow-2xl relative">
            <button
              onClick={() => setSelectedId(null)}
              className="absolute top-3 right-3 w-8 h-8 border border-neutral-300 text-neutral-500 hover:text-neutral-900 hover:border-neutral-900"
              aria-label="Close"
              title="Close"
            >
              X
            </button>
            <h3 className="text-xl md:text-2xl font-black text-neutral-900 pr-10">{selected.title}</h3>
            <p className="mt-4 text-neutral-700 whitespace-pre-wrap">{selected.judgment}</p>
            <div className="mt-6 border border-neutral-200 p-3 min-h-[220px] flex items-center justify-center bg-neutral-50">
              {selectedImage ? (
                <img src={selectedImage} alt={`${selected.id}.png`} className="max-h-[300px] w-auto object-contain" />
              ) : (
                <span className="text-neutral-400 text-sm">{`${selected.id}.png`}</span>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="w-full text-center py-10 animate-ink">
        <h2 className="text-4xl font-black text-neutral-900 tracking-widest">{t.title}</h2>
        <p className="text-neutral-400 mt-3 font-light tracking-widest">{t.subtitle}</p>
      </div>

      <div className="w-full bg-white border-2 border-neutral-900 p-16 rounded-sm flex flex-col items-center gap-16 shadow-2xl relative">
        <div className="absolute top-8 left-8 seal-stamp text-xs opacity-40">{t.seal}</div>

        <div className="relative">
          <div className="absolute inset-0 bg-neutral-900/5 blur-[80px] rounded-full scale-125" />

          <div className="relative w-80 h-80 md:w-[500px] md:h-[500px] border-[1px] border-neutral-200 rounded-full flex items-center justify-center p-8 transition-transform hover:scale-105 duration-1000 ease-in-out">
            <div className="absolute w-24 h-24 md:w-40 md:h-40 bg-neutral-900 rounded-full shadow-2xl flex items-center justify-center border-4 border-white">
              <div className="text-white text-3xl md:text-5xl font-black opacity-80">{t.centerMark}</div>
            </div>

            <div className="grid grid-cols-8 gap-1 md:gap-2 z-10 p-4 bg-white/60 backdrop-blur-sm rounded-lg border border-neutral-100">
              {Array.from({ length: 64 }).map((_, i) => {
                const id = i + 1;
                const isDiscovered = !!discovered[id];
                return (
                  <button
                    key={id}
                    onClick={() => {
                      if (isDiscovered) {
                        setSelectedId(id);
                      }
                    }}
                    disabled={!isDiscovered}
                    className={`w-6 h-6 md:w-10 md:h-10 border rounded-sm flex items-center justify-center text-[8px] md:text-xs transition-all ${
                      isDiscovered
                        ? 'border-neutral-900 text-neutral-900 font-bold hover:bg-neutral-900 hover:text-white cursor-pointer'
                        : 'border-neutral-200 text-neutral-300 cursor-default'
                    }`}
                    title={fillTemplate(t.hexagramTitleTemplate, { id })}
                  >
                    {id}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 w-full text-center border-t border-neutral-100 pt-10">
          <div className="space-y-1">
            <div className="text-4xl font-black text-neutral-900">{loading ? '...' : `${discoveredCount} / 64`}</div>
            <div className="text-neutral-400 text-[10px] uppercase tracking-[0.3em] font-bold">{t.stats.discoveredLabel}</div>
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-black text-neutral-900">{readingCount}</div>
            <div className="text-neutral-400 text-[10px] uppercase tracking-[0.3em] font-bold">{t.stats.readingsLabel}</div>
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-black text-neutral-900">{stage}</div>
            <div className="text-neutral-400 text-[10px] uppercase tracking-[0.3em] font-bold">{t.stats.stageLabel}</div>
          </div>
        </div>

        <p className="text-neutral-300 italic text-sm font-light tracking-[0.5em] pt-4">{t.footer}</p>
      </div>
    </div>
  );
};

export default Achievements;
