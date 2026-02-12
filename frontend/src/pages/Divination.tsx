
import React, { useState } from 'react';
import { api } from '../services/api';
import { IChingValue, singleYarrowThrow, processThrows } from '../utils/iching';
import HexagramDisplay from '../components/HexagramDisplay';
import { DivinationJsonResponse, UserProfile } from '../types';

interface DivinationProps {
  user: UserProfile;
  onUserUpdate: (user: UserProfile) => void;
}

const Divination: React.FC<DivinationProps> = ({ user, onUserUpdate }) => {
  const [question, setQuestion] = useState('');
  const [isThrowing, setIsThrowing] = useState(false);
  const [currentThrows, setCurrentThrows] = useState<IChingValue[]>([]);
  
  // Step 1: Local result
  const [localResult, setLocalResult] = useState<{name: string, judgment: string, lines: string} | null>(null);
  
  // Step 2: Server interpretation
  const [aiReading, setAiReading] = useState<DivinationJsonResponse | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [showAdDialog, setShowAdDialog] = useState(false);

  const startCasting = async () => {
    if (!question.trim()) {
      alert('請先輸入您想請示的問題');
      return;
    }

    setIsThrowing(true);
    setAiReading(null);
    setLocalResult(null);
    setCurrentThrows([]);

    const newThrows: IChingValue[] = [];
    for (let i = 0; i < 6; i++) {
      await new Promise(resolve => setTimeout(resolve, 400));
      const val = singleYarrowThrow();
      newThrows.push(val);
      setCurrentThrows([...newThrows]);
    }

    const { binaryCode, changingLines } = processThrows(newThrows);
    
    // Simulating local DB lookup for hexagram text
    // In a real app, this would query a local SQLite or a predefined map
    const mockHexName = `第 ${parseInt(binaryCode, 2) + 1} 卦`;
    const mockJudgment = `卦象編碼：${binaryCode}\n\n「天行健，君子以自強不息。」此乃天地交泰之象。`;
    let lineText = "";
    if (changingLines.length > 0) {
      lineText = changingLines.map(l => `${l} 爻：其道轉化，宜靜觀其變。`).join('\n');
    }

    setLocalResult({
      name: mockHexName,
      judgment: mockJudgment,
      lines: lineText
    });
    setIsThrowing(false);
  };

  const requestInterpretation = async (adToken?: string) => {
    setLoading(true);
    try {
      const response = await api.performDivination({
        question,
        throws: currentThrows,
      }, adToken);
      
      setAiReading(response);
      // Refresh user profile to update wallet
      const updatedProfile = await api.getMe();
      onUserUpdate(updatedProfile);
    } catch (error: any) {
      if (error.message === 'INSUFFICIENT_FUNDS') {
        setShowAdDialog(true);
      } else {
        alert('解析失敗：' + error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInterpretationClick = () => {
    if (user.wallet.gold === 0 && user.wallet.silver === 0) {
      setShowAdDialog(true);
    } else {
      requestInterpretation();
    }
  };

  const handleWatchAd = async () => {
    setShowAdDialog(false);
    setLoading(true);
    try {
      // Simulate watching ad and getting proof
      const adRes = await api.completeAd({ provider: 'unknown', ad_proof: 'mock_proof' });
      if ('ad_session_token' in adRes) {
        await requestInterpretation(adRes.ad_session_token);
      } else {
        // If it granted silver instead
        const updatedProfile = await api.getMe();
        onUserUpdate(updatedProfile);
        await requestInterpretation();
      }
    } catch (e) {
      alert('廣告載入失敗');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center w-full max-w-xl mx-auto space-y-10 pb-32">
      {/* Ad Dialog Overlay */}
      {showAdDialog && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/40 backdrop-blur-sm">
          <div className="bg-white border-2 border-neutral-900 p-8 max-w-sm w-full animate-ink shadow-2xl">
            <h3 className="text-2xl font-black text-neutral-900 mb-4 tracking-widest">奉納不足</h3>
            <p className="text-neutral-600 mb-8 leading-relaxed font-serif-tc">
              囊中羞澀，無法請示宗師。是否願觀賞一段「仙山雲影」（廣告）以換取一次解卦機會？
            </p>
            <div className="space-y-3">
              <button 
                onClick={handleWatchAd}
                className="w-full py-4 bg-neutral-900 text-white font-bold tracking-widest hover:bg-black transition"
              >
                誠心觀看
              </button>
              <button 
                onClick={() => setShowAdDialog(false)}
                className="w-full py-4 border-2 border-neutral-900 text-neutral-900 font-bold tracking-widest hover:bg-neutral-50 transition"
              >
                暫且作罷
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="w-full text-center space-y-6 pt-10 animate-ink">
        <div className="inline-block relative">
          <h2 className="text-3xl font-black text-neutral-900 tracking-[0.3em]">誠心求卜</h2>
          <div className="absolute -bottom-2 left-0 right-0 h-1 bg-neutral-900/10"></div>
        </div>
        
        <div className="relative">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={isThrowing || loading || !!localResult}
            placeholder="請在此輸入您的疑惑..."
            className="w-full bg-transparent border-b-2 border-neutral-300 p-6 text-neutral-900 placeholder-neutral-400 focus:outline-none focus:border-neutral-900 transition-all min-h-[100px] resize-none text-center font-serif-tc text-xl"
          />
        </div>
      </div>

      <div className="relative flex flex-col items-center justify-center min-h-[300px] w-full bg-white/40 border-2 border-dashed border-neutral-200 rounded-3xl p-10">
        {currentThrows.length > 0 ? (
          <div className="animate-ink flex flex-col items-center">
            <HexagramDisplay throws={currentThrows} size="lg" />
            <p className="mt-8 text-neutral-400 text-xs uppercase tracking-[0.4em]">
              {currentThrows.length < 6 ? `正在成卦：第 ${currentThrows.length + 1} 爻` : '卦象已成'}
            </p>
          </div>
        ) : (
          <div className="text-center text-neutral-300 font-light tracking-widest italic">
            「專志凝神，感通天地」
          </div>
        )}

        {loading && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center rounded-3xl z-10">
            <div className="flex flex-col items-center gap-4">
              <div className="w-10 h-10 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-neutral-900 font-bold tracking-widest">天機演化中...</p>
            </div>
          </div>
        )}
      </div>

      {!isThrowing && !loading && !localResult && (
        <button
          onClick={startCasting}
          className="group relative px-16 py-5 bg-neutral-900 text-white rounded-sm transition-all hover:bg-black active:scale-95 shadow-2xl"
        >
          <span className="relative font-bold tracking-[0.5em] text-lg">揲蓍起卦</span>
        </button>
      )}

      {localResult && (
        <div className="w-full space-y-8 animate-ink">
          {/* Step 1 Result Card */}
          <div className="bg-white border-2 border-neutral-900 p-8 rounded-sm shadow-xl relative">
            <div className="seal-stamp text-xs absolute top-4 right-4">初占結果</div>
            <h3 className="text-3xl font-black text-neutral-900 mb-6">{localResult.name}</h3>
            <div className="prose max-w-none text-neutral-800 font-serif-tc text-lg leading-relaxed whitespace-pre-wrap">
              {localResult.judgment}
            </div>
            {localResult.lines && (
              <div className="mt-6 pt-6 border-t border-neutral-100">
                <h4 className="text-red-700 font-bold text-sm tracking-widest mb-3">變爻辭</h4>
                <p className="text-neutral-600 text-sm whitespace-pre-wrap">{localResult.lines}</p>
              </div>
            )}
          </div>

          {/* Step 2 Trigger / AI Result */}
          {!aiReading ? (
            <div className="text-center py-4">
              <button
                onClick={handleInterpretationClick}
                className="px-12 py-5 bg-red-700 text-white rounded-sm font-bold tracking-[0.3em] hover:bg-red-800 transition shadow-lg flex items-center gap-4 mx-auto"
              >
                <span>請宗師深度解卦</span>
                <span className="text-xs opacity-60 font-sans tracking-normal">(消耗 1 銀幣)</span>
              </button>
              <button 
                onClick={() => { setLocalResult(null); setCurrentThrows([]); setQuestion(''); }}
                className="mt-6 text-neutral-400 hover:text-neutral-900 text-sm tracking-widest block mx-auto"
              >
                重啟一卦
              </button>
            </div>
          ) : (
            <div className="bg-neutral-900 text-white p-10 rounded-sm shadow-2xl space-y-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
                <span className="text-8xl">📜</span>
              </div>
              <h3 className="text-xl font-bold tracking-[0.4em] text-neutral-400 uppercase border-b border-neutral-800 pb-4">宗師深度解析</h3>
              <div className="prose prose-invert max-w-none text-neutral-200 font-serif-tc text-xl leading-[2.2] whitespace-pre-wrap">
                {aiReading.content}
              </div>
              <button 
                onClick={() => { setLocalResult(null); setAiReading(null); setCurrentThrows([]); setQuestion(''); }}
                className="w-full py-4 mt-10 text-neutral-500 hover:text-white text-sm font-medium transition border-t border-neutral-800"
              >
                感恩教誨，再次問卜
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Divination;
