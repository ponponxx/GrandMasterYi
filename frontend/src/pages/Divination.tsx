import React, { useState } from 'react';

import HexagramDisplay from '../components/HexagramDisplay';
import { useI18n } from '../i18n';
import { api } from '../services/api';
import { lookupHexagramByThrows } from '../services/ichingLocal';
import { saveOfflineReading } from '../services/offlineHistoryDb';
import { DivinationJsonResponse, TokenUsage, UserProfile } from '../types';
import { IChingValue, singleYarrowThrow } from '../utils/iching';

interface DivinationProps {
  user: UserProfile;
  onUserUpdate: (user: UserProfile) => void;
}

interface LocalResult {
  name: string;
  judgment: string;
  lines: string;
}

const fillTemplate = (template: string, vars: Record<string, string | number>) => {
  let out = template;
  Object.entries(vars).forEach(([key, value]) => {
    out = out.replace(`{${key}}`, String(value));
  });
  return out;
};

const Divination: React.FC<DivinationProps> = ({ user, onUserUpdate }) => {
  const { messages } = useI18n();
  const t = messages.divination;
  const [question, setQuestion] = useState('');
  const [isThrowing, setIsThrowing] = useState(false);
  const [currentThrows, setCurrentThrows] = useState<IChingValue[]>([]);
  const [localResult, setLocalResult] = useState<LocalResult | null>(null);
  const [aiReading, setAiReading] = useState<DivinationJsonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [showAdDialog, setShowAdDialog] = useState(false);

  const createEmptyAiReading = (): DivinationJsonResponse => ({
    reading_id: null,
    hexagram_code: '',
    changing_lines: [],
    content: '',
    saved_to_history: false,
  });

  const resetReading = () => {
    setLocalResult(null);
    setAiReading(null);
    setCurrentThrows([]);
    setQuestion('');
  };

  const logTokenUsage = (usage: TokenUsage) => {
    console.info('[Divination][TokenUsage]', {
      title: t.tokenUsage.title,
      input_label: t.tokenUsage.inputLabel,
      input_tokens: usage.input_tokens,
      output_label: t.tokenUsage.outputLabel,
      output_tokens: usage.output_tokens,
      total_label: t.tokenUsage.totalLabel,
      total_tokens: usage.total_tokens,
    });
  };

  const startCasting = async () => {
    setIsThrowing(true);
    setAiReading(null);
    setLocalResult(null);
    setCurrentThrows([]);

    const newThrows: IChingValue[] = [];
    for (let i = 0; i < 6; i++) {
      await new Promise((resolve) => setTimeout(resolve, 400));
      const val = singleYarrowThrow();
      newThrows.push(val);
      setCurrentThrows([...newThrows]);
    }

    try {
      const context = await lookupHexagramByThrows(newThrows);
      const headerName = fillTemplate(t.localResult.titleTemplate, {
        id: context.hexagramId,
        name: context.displayName,
      });
      const summary = context.trigramTitle
        ? `${context.trigramTitle}${t.localResult.summaryJoiner}${context.judgment}`
        : context.judgment;
      const lineText = context.changingLineTexts.join('\n');

      try {
        await saveOfflineReading({
          question: question.trim(),
          throws: newThrows,
          hexagram_id: context.hexagramId,
          hexagram_code: context.hexagramCode,
          hexagram_name: context.hexagramName,
          display_name: context.displayName,
          trigram_title: context.trigramTitle,
          judgment: context.judgment,
          changing_lines: context.changingLines,
          changing_line_texts: context.changingLineTexts,
        });
      } catch (saveError) {
        console.error(saveError);
      }

      setLocalResult({
        name: headerName,
        judgment: summary,
        lines: lineText,
      });
    } catch (error: any) {
      alert(`${t.alerts.lookupFailedPrefix}${error?.message || t.alerts.unknownError}`);
    } finally {
      setIsThrowing(false);
    }
  };

  const requestInterpretation = async (adToken?: string) => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      alert(t.alerts.missingQuestion);
      return;
    }

    setLoading(true);
    const initialReading = createEmptyAiReading();
    setAiReading(initialReading);

    try {
      const streamResult = await api.performDivinationStream(
        {
          question: trimmedQuestion,
          throws: currentThrows,
        },
        (chunk) => {
          setAiReading((prev) => {
            const current = prev ?? initialReading;
            return {
              ...current,
              content: `${current.content}${chunk}`,
            };
          });
        },
        adToken
      );

      console.info('[Divination][StreamResult]', streamResult);
      if (streamResult.tokenUsage) {
        logTokenUsage(streamResult.tokenUsage);
      } else {
        console.warn('[Divination][TokenUsage] missing from stream response');
      }

      setAiReading((prev) => (prev ? { ...prev, saved_to_history: true } : prev));
      const updatedProfile = await api.getMe();
      onUserUpdate(updatedProfile);
    } catch (error: any) {
      if (error.message === 'INSUFFICIENT_FUNDS') {
        setShowAdDialog(true);
      } else {
        alert(`${t.alerts.interpretationFailedPrefix}${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInterpretationClick = () => {
    if (!question.trim()) {
      alert(t.alerts.missingQuestion);
      return;
    }

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
      const adRes = await api.completeAd({ provider: 'unknown', ad_proof: 'mock_proof' });
      if ('ad_session_token' in adRes) {
        await requestInterpretation(adRes.ad_session_token);
      } else {
        const updatedProfile = await api.getMe();
        onUserUpdate(updatedProfile);
        await requestInterpretation();
      }
    } catch {
      alert(t.alerts.adFailed);
    } finally {
      setLoading(false);
    }
  };

  const castingStatusText =
    currentThrows.length < 6
      ? t.status.castingLine.replace('{line}', String(currentThrows.length + 1))
      : t.status.castingDone;

  return (
    <div className="flex flex-col items-center w-full max-w-xl mx-auto space-y-10 pb-32">
      {showAdDialog && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/40 backdrop-blur-sm">
          <div className="bg-white border-2 border-neutral-900 p-8 max-w-sm w-full animate-ink shadow-2xl">
            <h3 className="text-2xl font-black text-neutral-900 mb-4 tracking-widest">{t.adDialog.title}</h3>
            <p className="text-neutral-600 mb-8 leading-relaxed font-serif-tc">{t.adDialog.description}</p>
            <div className="space-y-3">
              <button
                onClick={handleWatchAd}
                className="w-full py-4 bg-neutral-900 text-white font-bold tracking-widest hover:bg-black transition"
              >
                {t.adDialog.watchButton}
              </button>
              <button
                onClick={() => setShowAdDialog(false)}
                className="w-full py-4 border-2 border-neutral-900 text-neutral-900 font-bold tracking-widest hover:bg-neutral-50 transition"
              >
                {t.adDialog.cancelButton}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="w-full text-center space-y-6 pt-10 animate-ink">
        <div className="inline-block relative">
          <h2 className="text-3xl font-black text-neutral-900 tracking-[0.3em]">{t.header.title}</h2>
          <div className="absolute -bottom-2 left-0 right-0 h-1 bg-neutral-900/10" />
        </div>

        <div className="relative">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={isThrowing || loading}
            placeholder={t.header.questionPlaceholder}
            className="w-full bg-transparent border-b-2 border-neutral-300 p-6 text-neutral-900 placeholder-neutral-400 focus:outline-none focus:border-neutral-900 transition-all min-h-[100px] resize-none text-center font-serif-tc text-xl"
          />
        </div>
      </div>

      <div className="relative flex flex-col items-center justify-center min-h-[300px] w-full bg-white/40 border-2 border-dashed border-neutral-200 rounded-3xl p-10">
        {currentThrows.length > 0 ? (
          <div className="animate-ink flex flex-col items-center">
            <HexagramDisplay throws={currentThrows} size="lg" />
            <p className="mt-8 text-neutral-400 text-xs uppercase tracking-[0.4em]">{castingStatusText}</p>
          </div>
        ) : (
          <div className="text-center text-neutral-300 font-light tracking-widest italic">{t.status.idleHint}</div>
        )}

        {loading && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center rounded-3xl z-10">
            <div className="flex flex-col items-center gap-4">
              <div className="w-10 h-10 border-2 border-neutral-900 border-t-transparent rounded-full animate-spin" />
              <p className="text-neutral-900 font-bold tracking-widest">{t.status.loading}</p>
            </div>
          </div>
        )}
      </div>

      {!isThrowing && !loading && !localResult && (
        <button
          onClick={startCasting}
          className="group relative px-16 py-5 bg-neutral-900 text-white rounded-sm transition-all hover:bg-black active:scale-95 shadow-2xl"
        >
          <span className="relative font-bold tracking-[0.5em] text-lg">{t.buttons.startCasting}</span>
        </button>
      )}

      {localResult && (
        <div className="w-full space-y-8 animate-ink">
          <div className="bg-white border-2 border-neutral-900 p-8 rounded-sm shadow-xl relative">
            <div className="seal-stamp text-xs absolute top-4 right-4">{t.localResult.seal}</div>
            <h3 className="text-3xl font-black text-neutral-900 mb-6">{localResult.name}</h3>
            <p className="text-xs tracking-widest text-neutral-400 mb-4">
              {t.localResult.throwsLabel} [{currentThrows.join(',')}]
            </p>
            <div className="prose max-w-none text-neutral-800 font-serif-tc text-lg leading-relaxed whitespace-pre-wrap">
              {localResult.judgment}
            </div>
            {localResult.lines && (
              <div className="mt-6 pt-6 border-t border-neutral-100">
                <h4 className="text-red-700 font-bold text-sm tracking-widest mb-3">{t.localResult.changingLinesTitle}</h4>
                <p className="text-neutral-600 text-sm whitespace-pre-wrap">{localResult.lines}</p>
              </div>
            )}
          </div>

          {!aiReading ? (
            <div className="text-center py-4">
              <button
                onClick={handleInterpretationClick}
                className="px-12 py-5 bg-red-700 text-white rounded-sm font-bold tracking-[0.3em] hover:bg-red-800 transition shadow-lg flex items-center gap-4 mx-auto"
              >
                <span>{t.buttons.askAi}</span>
                <span className="text-xs opacity-60 font-sans tracking-normal">{t.aiResult.costHint}</span>
              </button>
              <button
                onClick={resetReading}
                className="mt-6 text-neutral-400 hover:text-neutral-900 text-sm tracking-widest block mx-auto"
              >
                {t.buttons.reset}
              </button>
            </div>
          ) : (
            <div className="bg-neutral-900 text-white p-10 rounded-sm shadow-2xl space-y-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
                <span className="text-8xl">{t.aiResult.cornerMark}</span>
              </div>
              <h3 className="text-xl font-bold tracking-[0.4em] text-neutral-400 uppercase border-b border-neutral-800 pb-4">
                {t.aiResult.title}
              </h3>
              <div className="prose prose-invert max-w-none text-neutral-200 font-serif-tc text-xl leading-[2.2] whitespace-pre-wrap">
                {aiReading.content}
              </div>
              <button
                onClick={resetReading}
                className="w-full py-4 mt-10 text-neutral-500 hover:text-white text-sm font-medium transition border-t border-neutral-800"
              >
                {t.buttons.newReading}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Divination;
