import Constants from 'expo-constants';

export interface CatalogEntry {
  title: string;
  author: string;
  alternate_titles?: string;
}

export interface ScanCandidate extends CatalogEntry {
  confidence: number;
  title_score: number;
  author_score: number;
}

export interface ScanReading {
  title: string | null;
  author: string | null;
  error?: string;
}

export type ScanBookStatus = 'auto_matched' | 'needs_review' | 'unmatched';

export interface ScanBookResult {
  crop: string;
  reading: ScanReading;
  match: CatalogEntry | null;
  candidates: ScanCandidate[];
  ambiguous: boolean;
  confidence: number;
  title_score: number;
  author_score: number;
  status: ScanBookStatus;
  saved_book_id: number | null;
}

export interface ScanResponse {
  status: string;
  message: string;
  detection_count: number;
  crop_count: number;
  books: ScanBookResult[];
  latency_seconds: number;
}

export interface Book {
  id: number;
  title: string;
  author: string;
  confidence: number;
  added_at: string;
}

// In LAN mode, hostUri is the dev machine's real LAN IP, so it can be reused
// for the API. In tunnel mode (`expo start --tunnel`), hostUri is a public
// ngrok hostname that does not proxy Django, so it must be overridden — see
// EXPO_PUBLIC_API_BASE_URL in the README.
function resolveApiBaseUrl(): string {
  const envOverride = process.env.EXPO_PUBLIC_API_BASE_URL;
  if (envOverride) {
    return envOverride;
  }

  const hostUri = Constants.expoConfig?.hostUri ?? Constants.expoGoConfig?.hostUri;
  const host = hostUri?.split(':')[0];
  if (host) {
    return `http://${host}:8000/api`;
  }
  return 'http://127.0.0.1:8000/api';
}

export const API_BASE_URL = resolveApiBaseUrl();

// Upload a photo to the scan pipeline and return per-book detections/matches.
export async function scanPhoto(photoUri: string): Promise<ScanResponse> {
  const filename = photoUri.split('/').pop() || 'scan.jpg';
  const extensionMatch = /\.(\w+)$/.exec(filename);
  const extension = extensionMatch ? extensionMatch[1].toLowerCase() : 'jpg';
  const mimeType = `image/${extension === 'jpg' ? 'jpeg' : extension}`;

  const formData = new FormData();
  formData.append('photo', {
    uri: photoUri,
    name: filename,
    type: mimeType,
  } as unknown as Blob);

  const response = await fetch(`${API_BASE_URL}/scan/`, {
    method: 'POST',
    body: formData,
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Scan request failed with status ${response.status}`);
  }

  return response.json();
}

export async function fetchBooks(): Promise<Book[]> {
  const response = await fetch(`${API_BASE_URL}/books/`);
  if (!response.ok) {
    throw new Error(`Failed to load library (status ${response.status})`);
  }
  return response.json();
}

// Confirm/Correct both call this — the caller decides which title/author to send.
export async function createBook(
  title: string,
  author: string,
  confidence: number
): Promise<Book> {
  const response = await fetch(`${API_BASE_URL}/books/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, author, confidence }),
  });

  if (!response.ok) {
    throw new Error(`Failed to save book (status ${response.status})`);
  }

  return response.json();
}
