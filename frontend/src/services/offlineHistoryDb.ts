import type { IChingValue } from '../utils/iching';

const DB_NAME = 'masteryi_local';
const DB_VERSION = 1;
const OFFLINE_READINGS_STORE = 'offline_readings';
const OFFLINE_HISTORY_UPDATED_EVENT = 'offline-history-updated';

export interface OfflineReadingRecord {
  id?: number;
  question: string;
  throws: IChingValue[];
  hexagram_id: number;
  hexagram_code: string;
  hexagram_name: string;
  display_name: string;
  trigram_title: string;
  judgment: string;
  changing_lines: number[];
  changing_line_texts: string[];
  created_at: string;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(OFFLINE_READINGS_STORE)) {
        const store = db.createObjectStore(OFFLINE_READINGS_STORE, {
          keyPath: 'id',
          autoIncrement: true,
        });
        store.createIndex('created_at', 'created_at', { unique: false });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error('indexeddb_open_failed'));
  });
}

function withStore<T>(
  mode: IDBTransactionMode,
  handler: (store: IDBObjectStore, resolve: (value: T) => void, reject: (reason?: unknown) => void) => void
): Promise<T> {
  return new Promise(async (resolve, reject) => {
    let db: IDBDatabase;
    try {
      db = await openDb();
    } catch (error) {
      reject(error);
      return;
    }

    const tx = db.transaction(OFFLINE_READINGS_STORE, mode);
    const store = tx.objectStore(OFFLINE_READINGS_STORE);
    handler(store, resolve, reject);
    tx.oncomplete = () => db.close();
    tx.onerror = () => {
      reject(tx.error || new Error('indexeddb_tx_failed'));
      db.close();
    };
    tx.onabort = () => db.close();
  });
}

function emitOfflineHistoryUpdated() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(OFFLINE_HISTORY_UPDATED_EVENT));
  }
}

export async function saveOfflineReading(
  input: Omit<OfflineReadingRecord, 'id' | 'created_at'> & { created_at?: string }
): Promise<number> {
  const record: OfflineReadingRecord = {
    ...input,
    created_at: input.created_at || new Date().toISOString(),
  };

  return withStore<number>('readwrite', (store, resolve, reject) => {
    const request = store.add(record);
    request.onsuccess = () => {
      emitOfflineHistoryUpdated();
      resolve(Number(request.result));
    };
    request.onerror = () => reject(request.error || new Error('offline_reading_save_failed'));
  });
}

export async function listOfflineReadings(limit = 200): Promise<OfflineReadingRecord[]> {
  const all = await withStore<OfflineReadingRecord[]>('readonly', (store, resolve, reject) => {
    const request = store.getAll();
    request.onsuccess = () => resolve((request.result || []) as OfflineReadingRecord[]);
    request.onerror = () => reject(request.error || new Error('offline_reading_list_failed'));
  });

  return all
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, limit);
}

export async function deleteOfflineReading(id: number): Promise<void> {
  await withStore<void>('readwrite', (store, resolve, reject) => {
    const request = store.delete(id);
    request.onsuccess = () => {
      emitOfflineHistoryUpdated();
      resolve();
    };
    request.onerror = () => reject(request.error || new Error('offline_reading_delete_failed'));
  });
}

export { OFFLINE_HISTORY_UPDATED_EVENT };
