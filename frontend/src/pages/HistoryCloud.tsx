import React, { useEffect, useState } from 'react';

import { useI18n } from '../i18n';
import { lookupHexagramByCodeAndLines } from '../services/ichingLocal';
import { api } from '../services/api';
import { HistoryDetailResponse, HistoryListItem } from '../types';

type DetailState = Record<number, HistoryDetailResponse>;
type HexagramState = Record<
  number,
  {
    title: string;
    summary: string;
    lines: string;
  }
>;

const fillTemplate = (template: string, vars: Record<string, string | number>) => {
  let out = template;
  Object.entries(vars).forEach(([key, value]) => {
    out = out.replace(`{${key}}`, String(value));
  });
  return out;
};

interface HistoryCloudProps {
  reloadToken?: number;
}

const HistoryCloud: React.FC<HistoryCloudProps> = ({ reloadToken = 0 }) => {
  const { messages } = useI18n();
  const t = messages.ui.historyCloud;
  const [history, setHistory] = useState<HistoryListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [pinningId, setPinningId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [loadingDetailId, setLoadingDetailId] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [details, setDetails] = useState<DetailState>({});
  const [hexagrams, setHexagrams] = useState<HexagramState>({});

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const res = await api.getHistory();
        setHistory(res.items);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [reloadToken]);

  const togglePin = async (id: number, currentPinned: boolean) => {
    const nextPinned = !currentPinned;
    setPinningId(id);
    setHistory((prev) => prev.map((item) => (item.reading_id === id ? { ...item, is_pinned: nextPinned } : item)));

    try {
      await api.pinHistory(id, nextPinned);
    } catch (error) {
      setHistory((prev) => prev.map((item) => (item.reading_id === id ? { ...item, is_pinned: currentPinned } : item)));
      console.error(error);
      alert(t.alerts.pinFailed);
    } finally {
      setPinningId(null);
    }
  };

  const loadDetail = async (readingId: number) => {
    if (details[readingId]) {
      setExpanded((prev) => ({ ...prev, [readingId]: !prev[readingId] }));
      return;
    }

    setLoadingDetailId(readingId);
    try {
      const detail = await api.getHistoryDetail(readingId);
      setDetails((prev) => ({ ...prev, [readingId]: detail }));
      setExpanded((prev) => ({ ...prev, [readingId]: true }));

      try {
        const context = await lookupHexagramByCodeAndLines(detail.hexagram_code, detail.changing_lines);
        setHexagrams((prev) => ({
          ...prev,
          [readingId]: {
            title: fillTemplate(t.hexagramTitleTemplate, {
              id: context.hexagramId,
              name: context.displayName,
            }),
            summary: context.trigramTitle
              ? `${context.trigramTitle}${t.summaryJoiner}${context.judgment}`
              : context.judgment,
            lines: context.changingLineTexts.join('\n'),
          },
        }));
      } catch (error) {
        console.error(error);
      }
    } catch (error) {
      console.error(error);
      alert(t.alerts.loadDetailFailed);
    } finally {
      setLoadingDetailId(null);
    }
  };

  const openDeleteConfirm = (readingId: number) => {
    setConfirmDeleteId(readingId);
  };

  const cancelDelete = () => {
    setConfirmDeleteId(null);
  };

  const handleDelete = async () => {
    if (confirmDeleteId === null) {
      return;
    }

    const readingId = confirmDeleteId;
    setDeletingId(readingId);
    try {
      await api.deleteHistory(readingId);
      setHistory((prev) => prev.filter((item) => item.reading_id !== readingId));
      setExpanded((prev) => {
        const next = { ...prev };
        delete next[readingId];
        return next;
      });
      setDetails((prev) => {
        const next = { ...prev };
        delete next[readingId];
        return next;
      });
      setHexagrams((prev) => {
        const next = { ...prev };
        delete next[readingId];
        return next;
      });
      setConfirmDeleteId(null);
    } catch (error) {
      console.error(error);
      alert('Failed to delete cloud history.');
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

  if (history.length === 0) {
    return (
      <div className="text-center py-20 border-2 border-dashed border-neutral-200 rounded-3xl">
        <p className="text-neutral-300 italic font-light tracking-widest">{t.emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {confirmDeleteId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-sm bg-white border-2 border-neutral-900 p-6 rounded-sm shadow-2xl">
            <h3 className="text-xl font-black text-neutral-900 tracking-wide">刪除雲端紀錄</h3>
            <p className="text-neutral-600 mt-3 text-sm leading-relaxed">確定要刪除這筆雲端占卜紀錄嗎？此操作無法復原。</p>
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleDelete}
                disabled={deletingId === confirmDeleteId}
                className="flex-1 py-2 border border-red-700 bg-red-700 text-white text-sm tracking-widest hover:bg-red-800 transition"
              >
                確認刪除
              </button>
              <button
                onClick={cancelDelete}
                disabled={deletingId === confirmDeleteId}
                className="flex-1 py-2 border border-neutral-300 text-neutral-700 text-sm tracking-widest hover:border-neutral-900 hover:text-neutral-900 transition"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}

      {history.map((item) => {
        const detail = details[item.reading_id];
        const context = hexagrams[item.reading_id];
        const isExpanded = !!expanded[item.reading_id];

        return (
          <article
            key={item.reading_id}
            className="bg-white border-b-2 border-neutral-100 p-8 transition-all hover:bg-neutral-50 relative overflow-hidden"
          >
            {item.is_pinned && <div className="absolute top-0 left-0 w-1 h-full bg-red-700" />}

            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-neutral-800 font-bold text-xl mb-2">
                  {t.questionPrefix}
                  {item.question}
                  {t.questionSuffix}
                </p>
                <div className="flex items-center gap-3 text-neutral-400 text-[10px] uppercase tracking-widest">
                  <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  <span>{t.metaSeparator}</span>
                  <span>#{item.reading_id}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  disabled={loadingDetailId === item.reading_id}
                  onClick={() => loadDetail(item.reading_id)}
                  className="px-3 py-2 border border-neutral-300 text-xs tracking-widest hover:border-neutral-900 transition"
                >
                  {isExpanded ? t.detailButtonHide : t.detailButtonShow}
                </button>
                <button
                  disabled={pinningId === item.reading_id}
                  onClick={() => togglePin(item.reading_id, item.is_pinned)}
                  className={`w-12 h-12 flex items-center justify-center rounded-full transition-all ${
                    item.is_pinned ? 'bg-red-50 text-red-700' : 'text-neutral-300 hover:text-neutral-900 hover:bg-neutral-100'
                  }`}
                >
                  {item.is_pinned ? <span className="text-xl">{t.pinIconOn}</span> : <span className="text-xl">{t.pinIconOff}</span>}
                </button>
                <button
                  disabled={deletingId === item.reading_id}
                  onClick={() => openDeleteConfirm(item.reading_id)}
                  className="px-3 py-2 border border-neutral-300 text-xs tracking-widest text-neutral-500 hover:text-red-700 hover:border-red-700 transition"
                >
                  刪除
                </button>
              </div>
            </div>

            {isExpanded && detail && (
              <div className="mt-6 pt-6 border-t border-neutral-100 space-y-4">
                <div className="space-y-2">
                  <h4 className="text-sm font-bold text-neutral-900 tracking-widest">{t.sectionHexagramContext}</h4>
                  <p className="text-neutral-800 whitespace-pre-wrap">
                    {context?.title || fillTemplate(t.fallbackHexagramTemplate, { code: detail.hexagram_code })}
                  </p>
                  <p className="text-neutral-700 whitespace-pre-wrap">{context?.summary || ''}</p>
                  {context?.lines && <p className="text-sm text-neutral-600 whitespace-pre-wrap">{context.lines}</p>}
                </div>
                <div className="space-y-2">
                  <h4 className="text-sm font-bold text-neutral-900 tracking-widest">{t.sectionInterpretation}</h4>
                  <p className="text-neutral-700 whitespace-pre-wrap">{detail.content}</p>
                </div>
              </div>
            )}
          </article>
        );
      })}
    </div>
  );
};

export default HistoryCloud;
