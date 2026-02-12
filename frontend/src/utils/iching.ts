
export type IChingValue = 6 | 7 | 8 | 9;

export function singleYarrowThrow(): IChingValue {
  let totalStalks = 49; // 50 stalks minus Taiji 1
  
  for (let i = 0; i < 3; i++) {
    // Simulate Random.secure() logic
    const left = Math.floor(Math.random() * (totalStalks - 1)) + 1;
    const right = totalStalks - left - 1;
    
    let remainderLeft = left % 4;
    if (remainderLeft === 0) remainderLeft = 4;
    
    let remainderRight = right % 4;
    if (remainderRight === 0) remainderRight = 4;
    
    totalStalks = totalStalks - (remainderLeft + remainderRight + 1);
  }

  const result = Math.floor(totalStalks / 4);
  switch (result) {
    case 6: return 6; // Old Yin
    case 7: return 7; // Young Yang
    case 8: return 8; // Young Yin
    case 9: return 9; // Old Yang
    default: return 8;
  }
}

export function processThrows(throws: IChingValue[]) {
  const binaryList: string[] = [];
  const changingLines: number[] = [];

  for (let i = 0; i < throws.length; i++) {
    const val = throws[i];
    if (val === 6) {
      binaryList.push("0");
      changingLines.push(i + 1);
    } else if (val === 7) {
      binaryList.push("1");
    } else if (val === 8) {
      binaryList.push("0");
    } else if (val === 9) {
      binaryList.push("1");
      changingLines.push(i + 1);
    }
  }

  // First throw is the bottom line (initial position)
  // Reversing to join gives the standard top-to-bottom binary representation? 
  // User snippet: binaryList.reversed.join()
  const binaryCode = [...binaryList].reverse().join("");

  return { binaryCode, changingLines };
}
