
import React from 'react';

const Shop: React.FC = () => {
  return (
    <div className="flex flex-col items-center w-full max-w-2xl mx-auto space-y-12 pb-32">
      <div className="w-full text-center py-10 animate-ink">
        <h2 className="text-4xl font-black text-neutral-900 tracking-widest">緣分奉納</h2>
        <p className="text-neutral-400 mt-3 font-light tracking-widest">Support the sanctuary of wisdom</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full">
        {/* Subscription */}
        <div className="bg-white border-2 border-neutral-900 p-10 rounded-sm flex flex-col items-center text-center space-y-6 hover:shadow-2xl transition-all group">
          <div className="w-16 h-16 bg-neutral-100 rounded-full flex items-center justify-center text-neutral-900 border border-neutral-200">
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
          <h3 className="text-2xl font-black text-neutral-900 tracking-widest">解惑大師</h3>
          <p className="text-neutral-500 text-sm leading-relaxed">
            無限起卦，深度詳解，<br/>尊享無廣告靜心空間。
          </p>
          <div className="text-3xl font-bold text-neutral-900 pt-4">
            NT$ 290<span className="text-xs text-neutral-400 font-normal"> / 月</span>
          </div>
          <button className="w-full py-4 bg-neutral-900 text-white font-bold transition hover:bg-black active:scale-95">
            即刻訂閱
          </button>
        </div>

        {/* Gold Package */}
        <div className="bg-white/60 border border-neutral-200 p-10 rounded-sm flex flex-col items-center text-center space-y-6 hover:bg-white hover:border-neutral-900 transition-all">
          <div className="w-16 h-16 bg-neutral-50 rounded-full flex items-center justify-center text-neutral-400 border border-neutral-100">
             <span className="text-2xl">🪙</span>
          </div>
          <h3 className="text-2xl font-black text-neutral-900 tracking-widest">百金錦囊</h3>
          <p className="text-neutral-500 text-sm leading-relaxed">
            兌換單次深度解析，<br/>適用於隨緣問卜。
          </p>
          <div className="text-3xl font-bold text-neutral-900 pt-4">NT$ 150</div>
          <button className="w-full py-4 border-2 border-neutral-900 text-neutral-900 font-bold transition hover:bg-neutral-50 active:scale-95">
            奉納金幣
          </button>
        </div>
      </div>

      <div className="w-full bg-neutral-900 text-white p-8 rounded-sm text-center shadow-xl">
        <p className="text-neutral-400 text-xs uppercase tracking-[0.3em] mb-4">目前結存</p>
        <div className="flex justify-center items-center gap-12">
          <div className="flex flex-col items-center">
            <span className="text-3xl font-bold">0</span>
            <span className="text-[10px] text-neutral-500 mt-1">金幣</span>
          </div>
          <div className="w-[1px] h-8 bg-neutral-800"></div>
          <div className="flex flex-col items-center">
            <span className="text-3xl font-bold">10</span>
            <span className="text-[10px] text-neutral-500 mt-1">銀幣</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Shop;
