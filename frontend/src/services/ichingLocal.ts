import initSqlJs, { Database, SqlJsStatic } from 'sql.js';
import sqlWasmUrl from 'sql.js/dist/sql-wasm.wasm?url';
import ichingDbUrl from '../../iching.db?url';
import type { IChingValue } from '../utils/iching';

export interface HexagramContext {
  hexagramId: number;
  hexagramCode: string;
  hexagramName: string;
  displayName: string;
  trigramTitle: string;
  judgment: string;
  changingLines: number[];
  changingLineTexts: string[];
}

type HexagramRow = {
  id: number | string;
  name: string;
  binary_code: string;
  judgment: string;
};

type LineRow = {
  position: string;
  position_num: number | string;
  text: string;
};

let sqlJsPromise: Promise<SqlJsStatic> | null = null;
let dbPromise: Promise<Database> | null = null;

function getSqlJs(): Promise<SqlJsStatic> {
  if (!sqlJsPromise) {
    sqlJsPromise = initSqlJs({
      locateFile: () => sqlWasmUrl,
    });
  }
  return sqlJsPromise;
}

async function getDb(): Promise<Database> {
  if (!dbPromise) {
    dbPromise = (async () => {
      const SQL = await getSqlJs();
      const response = await fetch(ichingDbUrl);
      if (!response.ok) {
        throw new Error(`failed_to_load_iching_db:${response.status}`);
      }
      const dbBytes = new Uint8Array(await response.arrayBuffer());
      return new SQL.Database(dbBytes);
    })();
  }
  return dbPromise;
}

function splitHexagramName(rawName: string): { displayName: string; trigramTitle: string } {
  const parts = rawName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return { displayName: rawName, trigramTitle: '' };
  }
  return {
    displayName: parts[0],
    trigramTitle: parts.slice(1).join(' '),
  };
}

function normalizeChangingLines(changingLines: number[]): number[] {
  return [...new Set(changingLines)]
    .map((value) => Number(value))
    .filter((value) => Number.isInteger(value) && value >= 1 && value <= 6)
    .sort((a, b) => a - b);
}

function ensureValidThrows(throws: IChingValue[]): void {
  if (!Array.isArray(throws) || throws.length !== 6) {
    throw new Error('invalid_throws');
  }
  const validValues = new Set([6, 7, 8, 9]);
  if (throws.some((value) => !validValues.has(value))) {
    throw new Error('invalid_throws');
  }
}

function buildHexagramCode(throws: IChingValue[]): string {
  const reversedThrows = [...throws].reverse();
  const topDownBits = reversedThrows.map((value) => (value === 7 || value === 9 ? '1' : '0'));
  return topDownBits.join('');
}

function changingLinesFromThrows(throws: IChingValue[]): number[] {
  const changing: number[] = [];
  throws.forEach((value, index) => {
    if (value === 6 || value === 9) {
      changing.push(index + 1);
    }
  });
  return changing;
}

async function lookupByCodeAndLines(hexagramCode: string, changingLines: number[]): Promise<HexagramContext> {
  const db = await getDb();
  const hexStmt = db.prepare(
    `
    SELECT id, name, binary_code, judgment
    FROM hexagrams
    WHERE binary_code = ?
    `
  );

  try {
    hexStmt.bind([hexagramCode]);
    if (!hexStmt.step()) {
      throw new Error(`hexagram_not_found_for_code:${hexagramCode}`);
    }

    const hexagram = hexStmt.getAsObject() as unknown as HexagramRow;
    const hexagramId = Number(hexagram.id);
    const hexagramName = String(hexagram.name || '').trim();
    const judgment = String(hexagram.judgment || '').trim();
    const normalizedLines = normalizeChangingLines(changingLines);
    const lineTexts: string[] = [];

    if (normalizedLines.length > 0) {
      const placeholders = normalizedLines.map(() => '?').join(',');
      const lineStmt = db.prepare(
        `
        SELECT position, position_num, text
        FROM lines
        WHERE hexagram_id = ?
          AND position_num IN (${placeholders})
        ORDER BY position_num
        `
      );

      try {
        lineStmt.bind([hexagramId, ...normalizedLines]);
        while (lineStmt.step()) {
          const row = lineStmt.getAsObject() as unknown as LineRow;
          const position = String(row.position || '').trim();
          const text = String(row.text || '').trim();
          if (position && text) {
            lineTexts.push(`${position}，${text}`);
          } else if (text) {
            lineTexts.push(text);
          }
        }
      } finally {
        lineStmt.free();
      }
    }

    const { displayName, trigramTitle } = splitHexagramName(hexagramName);
    return {
      hexagramId,
      hexagramCode: String(hexagram.binary_code || ''),
      hexagramName,
      displayName,
      trigramTitle,
      judgment,
      changingLines: normalizedLines,
      changingLineTexts: lineTexts,
    };
  } finally {
    hexStmt.free();
  }
}

export async function lookupHexagramByThrows(throws: IChingValue[]): Promise<HexagramContext> {
  ensureValidThrows(throws);
  const hexagramCode = buildHexagramCode(throws);
  const changingLines = changingLinesFromThrows(throws);
  return lookupByCodeAndLines(hexagramCode, changingLines);
}

export async function lookupHexagramByCodeAndLines(
  hexagramCode: string,
  changingLines: number[]
): Promise<HexagramContext> {
  const normalizedCode = String(hexagramCode || '').trim();
  if (!/^[01]{6}$/.test(normalizedCode)) {
    throw new Error('invalid_hexagram_code');
  }
  return lookupByCodeAndLines(normalizedCode, changingLines);
}
