
import React from 'react';

const Achievements: React.FC = () => {
  return (
    <div className="flex flex-col items-center w-full max-w-4xl mx-auto space-y-12 pb-32">
      <div className="w-full text-center py-10 animate-ink">
        <h2 className="text-4xl font-black text-neutral-900 tracking-widest">修行為要</h2>
        <p className="text-neutral-400 mt-3 font-light tracking-widest">The path of sixty-four changes</p>
      </div>

      <div className="w-full bg-white border-2 border-neutral-900 p-16 rounded-sm flex flex-col items-center gap-16 shadow-2xl relative">
        <div className="absolute top-8 left-8 seal-stamp text-xs opacity-40">天圓地方</div>
        
        <div className="relative">
          {/* Subtle ink glow behind the Bagua */}
          <div className="absolute inset-0 bg-neutral-900/5 blur-[80px] rounded-full scale-125"></div>
          
          <div className="relative w-80 h-80 md:w-[500px] md:h-[500px] border-[1px] border-neutral-200 rounded-full flex items-center justify-center p-8 transition-transform hover:scale-105 duration-1000 ease-in-out">
             {/* Center Yin Yang */}
             <div className="absolute w-24 h-24 md:w-40 md:h-40 bg-neutral-900 rounded-full shadow-2xl flex items-center justify-center border-4 border-white">
                <div className="text-white text-3xl md:text-5xl font-black opacity-80">☯</div>
             </div>

             {/* 64 Hexagram Grid arranged in a circle roughly */}
             <div className="grid grid-cols-8 gap-1 md:gap-2 z-10 p-4 bg-white/60 backdrop-blur-sm rounded-lg border border-neutral-100">
               {Array.from({ length: 64 }).map((_, i) => (
                 <div 
                   key={i} 
                   className="w-6 h-6 md:w-10 md:h-10 border border-neutral-100 rounded-sm flex items-center justify-center text-[8px] md:text-xs text-neutral-300 hover:bg-neutral-900 hover:text-white transition-all cursor-pointer hover:scale-110"
                   title={`Hexagram ${i + 1}`}
                 >
                   {i + 1}
                 </div>
               ))}
             </div>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 w-full text-center border-t border-neutral-100 pt-10">
          <div className="space-y-1">
            <div className="text-4xl font-black text-neutral-900">0 / 64</div>
            <div className="text-neutral-400 text-[10px] uppercase tracking-[0.3em] font-bold">卦象進度</div>
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-black text-neutral-900">0</div>
            <div className="text-neutral-400 text-[10px] uppercase tracking-[0.3em] font-bold">問卜總數</div>
          </div>
          <div className="space-y-1">
            <div className="text-4xl font-black text-neutral-900">1</div>
            <div className="text-neutral-400 text-[10px] uppercase tracking-[0.3em] font-bold">修道天數</div>
          </div>
        </div>

        <p className="text-neutral-300 italic text-sm font-light tracking-[0.5em] pt-4">成就系統，尚在演化中</p>
      </div>
    </div>
  );
};

export default Achievements;
