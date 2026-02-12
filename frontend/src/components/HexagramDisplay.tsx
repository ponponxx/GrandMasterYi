
import React from 'react';
import { IChingValue } from '../utils/iching';

interface HexagramDisplayProps {
  throws: IChingValue[];
  size?: 'sm' | 'md' | 'lg';
}

const HexagramDisplay: React.FC<HexagramDisplayProps> = ({ throws, size = 'md' }) => {
  const displayLines = [...throws].reverse();

  const containerWidths = {
    sm: 'w-24',
    md: 'w-36',
    lg: 'w-48',
  };

  const lineHeights = {
    sm: 'h-1.5 my-1',
    md: 'h-2.5 my-1.5',
    lg: 'h-3.5 my-2.5',
  };

  return (
    <div className={`flex flex-col items-center ${containerWidths[size]} relative`}>
      {displayLines.map((val, idx) => {
        const isYang = val === 7 || val === 9;
        const isChanging = val === 6 || val === 9;
        
        return (
          <div 
            key={idx} 
            className={`w-full relative ${lineHeights[size]} bg-neutral-900 rounded-sm overflow-hidden`}
          >
            {!isYang && <div className="yin-gap" />}
            {isChanging && (
              <div className="absolute inset-0 bg-neutral-900/10 mix-blend-overlay animate-pulse"></div>
            )}
            {/* Visual indicators for changing lines in traditional style */}
            {isChanging && (
              <div className="absolute -left-6 top-1/2 -translate-y-1/2 text-red-700 font-bold text-lg">
                {val === 9 ? '○' : '×'}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default HexagramDisplay;
