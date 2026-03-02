import React, { useEffect, useRef, useState } from 'react';

import { AdMob, RewardAdPluginEvents } from '@capacitor-community/admob';
import { Capacitor } from '@capacitor/core';
import type { PluginListenerHandle } from '@capacitor/core';

type RewardProvider = 'admob' | 'unknown';

interface RewardPayload {
  provider: RewardProvider;
  adProof: string;
}

interface AdRewardButtonProps {
  onRewardEarned: (payload: RewardPayload) => Promise<void>;
  disabled?: boolean;
  className?: string;
  labels?: {
    ready: string;
    loading: string;
    web: string;
    busy: string;
  };
}

const ANDROID_REWARDED_TEST_ID = 'ca-app-pub-3940256099942544/5224354917';
const IOS_REWARDED_TEST_ID = 'ca-app-pub-3940256099942544/1712485313';

const AdRewardButton: React.FC<AdRewardButtonProps> = ({
  onRewardEarned,
  disabled = false,
  className,
  labels,
}) => {
  const isNative = Capacitor.isNativePlatform();
  const [isAdReady, setIsAdReady] = useState(!isNative);
  const [isBusy, setIsBusy] = useState(false);
  const listenersRef = useRef<PluginListenerHandle[]>([]);
  const isMountedRef = useRef(true);

  const effectiveLabels = labels || {
    ready: 'Watch Ad +100 Silver',
    loading: 'Loading Ad...',
    web: 'Web Test: Watch Ad +100 Silver',
    busy: 'Processing...',
  };

  const loadRewardAd = async () => {
    if (!isNative) {
      setIsAdReady(true);
      return;
    }
    setIsAdReady(false);
    const adId = Capacitor.getPlatform() === 'ios' ? IOS_REWARDED_TEST_ID : ANDROID_REWARDED_TEST_ID;
    await AdMob.prepareRewardVideoAd({
      adId,
      isTesting: true,
    });
  };

  useEffect(() => {
    isMountedRef.current = true;
    if (!isNative) {
      setIsAdReady(true);
      return () => {
        isMountedRef.current = false;
      };
    }

    const setup = async () => {
      await AdMob.initialize({ initializeForTesting: true });
      const loadedListener = await AdMob.addListener(RewardAdPluginEvents.Loaded, () => {
        if (isMountedRef.current) {
          setIsAdReady(true);
        }
      });
      const failedListener = await AdMob.addListener(RewardAdPluginEvents.FailedToLoad, () => {
        if (isMountedRef.current) {
          setIsAdReady(false);
        }
      });
      listenersRef.current.push(loadedListener, failedListener);
      await loadRewardAd();
    };

    setup().catch((error) => {
      console.error(error);
      if (isMountedRef.current) {
        setIsAdReady(false);
      }
    });

    return () => {
      isMountedRef.current = false;
      listenersRef.current.forEach((listener) => listener.remove());
      listenersRef.current = [];
    };
  }, [isNative]);

  const handleClick = async () => {
    if (disabled || isBusy) {
      return;
    }
    setIsBusy(true);
    try {
      if (!isNative) {
        await new Promise((resolve) => setTimeout(resolve, 600));
        await onRewardEarned({
          provider: 'unknown',
          adProof: `web_mock_${Date.now()}`,
        });
        return;
      }

      const reward = await AdMob.showRewardVideoAd();
      await onRewardEarned({
        provider: 'admob',
        adProof: JSON.stringify(reward || {}),
      });
      await loadRewardAd();
    } catch (error) {
      console.error(error);
    } finally {
      if (isMountedRef.current) {
        setIsBusy(false);
      }
    }
  };

  const buttonText = isNative
    ? (isAdReady ? effectiveLabels.ready : effectiveLabels.loading)
    : effectiveLabels.web;

  return (
    <button
      onClick={handleClick}
      disabled={disabled || isBusy || (isNative && !isAdReady)}
      className={className}
    >
      {isBusy ? effectiveLabels.busy : buttonText}
    </button>
  );
};

export default AdRewardButton;
