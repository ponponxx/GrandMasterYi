import React, { useEffect, useState } from 'react';

import { useI18n } from '../i18n';
import { deleteOfflineReading, listOfflineReadings, OfflineReadingRecord } from '../services/offlineHistoryDb';

const fillTemplate = (template: string, vars: Record<string, string | number>) => {
  let out = template;
  Object.entries(vars).forEach(([key, value]) => {
    out = out.replace(`{${key}}`, String(value));
  });
  return out;
};

interface HistoryOfflineProps {
  reloadToken?: number;
}

const HistoryOffline: React.FC<HistoryOfflineProps> = ({ reloadToken = 0 }) => {
  const { messages } = useI18n();
  const t = messages.ui.historyOffline;
  const [items, setItems] = useState<OfflineReadingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const readings = await listOfflineReadings();
        setItems(readings);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [reloadToken]);

  const handleDelete = async (id?: number) => {
    if (typeof id !== 'number') {
      return;
    }
    setDeletingId(id);
    try {
      await deleteOfflineReading(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (error) {
      console.error(error);
      alert('Delete failed');
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[320px]">
        <div className="w-10 h-10 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-20 border-2 border-dashed border-neutral-200 rounded-3xl">
        <p className="text-neutral-300 italic font-light tracking-widest">{t.emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {items.map((item) => (
        <article
          key={item.id ?? `${item.created_at}-${item.hexagram_code}`}
          className="bg-white border-2 border-neutral-100 p-8 rounded-sm shadow-sm space-y-4 relative"
        >
          <button
            disabled={deletingId === item.id}
            onClick={() => handleDelete(item.id)}
            className="absolute top-3 right-3 w-7 h-7 border border-neutral-300 text-neutral-400 hover:text-red-700 hover:border-red-700 transition"
            title="Delete"
            aria-label="Delete"
          >
            X
          </button>
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-xl font-black text-neutral-900">
              {fillTemplate(t.titleTemplate, { id: item.hexagram_id, name: item.display_name })}
            </h3>
            <span className="text-[10px] tracking-widest text-neutral-400">{new Date(item.created_at).toLocaleString()}</span>
          </div>
          <p className="text-sm text-neutral-500">
            {t.questionPrefix}
            {item.question}
            {t.questionSuffix}
          </p>
          <p className="text-neutral-700 whitespace-pre-wrap">
            {item.trigram_title ? `${item.trigram_title}${t.summaryJoiner}${item.judgment}` : item.judgment}
          </p>
          {item.changing_line_texts.length > 0 && (
            <div className="border-t border-neutral-100 pt-4">
              <h4 className="text-xs font-bold tracking-widest text-red-700 mb-2">{t.changingLinesTitle}</h4>
              <p className="text-sm text-neutral-600 whitespace-pre-wrap">{item.changing_line_texts.join('\n')}</p>
            </div>
          )}
        </article>
      ))}
    </div>
  );
};

export default HistoryOffline;
