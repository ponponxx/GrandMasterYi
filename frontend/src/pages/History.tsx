
import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { HistoryListItem } from '../types';

const History: React.FC = () => {
  const [history, setHistory] = useState<HistoryListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await api.getHistory();
        setHistory(res.items);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  const togglePin = (id: number) => {
    setHistory(prev => prev.map(item => 
      item.reading_id === id ? { ...item, is_pinned: !item.is_pinned } : item
    ));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-10 h-10 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col w-full max-w-xl mx-auto space-y-8 pb-32">
      <div className="w-full text-center py-10 animate-ink">
        <h2 className="text-4xl font-black text-neutral-900 tracking-widest">問卜載錄</h2>
        <p className="text-neutral-400 mt-3 font-light tracking-widest">Chronicles of your destiny</p>
      </div>

      {history.length === 0 ? (
        <div className="text-center py-20 border-2 border-dashed border-neutral-200 rounded-3xl">
          <p className="text-neutral-300 italic font-light tracking-widest">「過往雲煙，尚未留痕」</p>
        </div>
      ) : (
        <div className="space-y-6">
          {history.map((item) => (
            <div 
              key={item.reading_id}
              className={`bg-white border-b-2 border-neutral-100 p-8 flex items-center justify-between transition-all hover:bg-neutral-50 group relative overflow-hidden`}
            >
              {item.is_pinned && (
                <div className="absolute top-0 left-0 w-1 h-full bg-red-700"></div>
              )}
              
              <div className="flex-1 min-w-0 pr-6">
                <p className="text-neutral-800 font-bold truncate text-xl mb-2 group-hover:text-neutral-900">
                   「{item.question}」
                </p>
                <div className="flex items-center gap-3 text-neutral-400 text-[10px] uppercase tracking-widest">
                  <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  <span>•</span>
                  <span>#{item.reading_id}</span>
                </div>
              </div>
              
              <button 
                onClick={() => togglePin(item.reading_id)}
                className={`w-12 h-12 flex items-center justify-center rounded-full transition-all ${item.is_pinned ? 'bg-red-50 text-red-700' : 'text-neutral-300 hover:text-neutral-900 hover:bg-neutral-100'}`}
              >
                {item.is_pinned ? (
                  <span className="text-xl">🔖</span>
                ) : (
                  <span className="text-xl">📍</span>
                )}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default History;
