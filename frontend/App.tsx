import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';

import PhotoCapture from './components/PhotoCapture';
import ReviewQueue, { ReviewQueueItem } from './components/ReviewQueue';
import BookList from './components/BookList';
import { Book, createBook, fetchBooks, scanPhoto } from './services/api';

interface ScanSummary {
  detectionCount: number;
  latencySeconds: number;
}

export default function App() {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [lastPhotoUri, setLastPhotoUri] = useState<string | null>(null);
  const [scanSummary, setScanSummary] = useState<ScanSummary | null>(null);
  const [autoSavedCount, setAutoSavedCount] = useState(0);
  const [reviewItems, setReviewItems] = useState<ReviewQueueItem[]>([]);
  const [savingItemId, setSavingItemId] = useState<string | null>(null);

  const [libraryBooks, setLibraryBooks] = useState<Book[]>([]);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [libraryError, setLibraryError] = useState<string | null>(null);

  const loadLibrary = useCallback(async () => {
    setLibraryLoading(true);
    setLibraryError(null);
    try {
      const books = await fetchBooks();
      setLibraryBooks(books);
    } catch {
      setLibraryError('Could not load your library.');
    } finally {
      setLibraryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  const runScan = useCallback(
    async (photoUri: string) => {
      setUploading(true);
      setUploadError(null);
      try {
        const result = await scanPhoto(photoUri);
        const autoSaved = result.books.filter((book) => book.status === 'auto_matched');
        const review: ReviewQueueItem[] = result.books
          .filter((book) => book.status !== 'auto_matched')
          .map((book, index) => ({ ...book, id: `${book.crop}-${index}` }));

        setAutoSavedCount(autoSaved.length);
        setReviewItems(review);
        setScanSummary({
          detectionCount: result.detection_count,
          latencySeconds: result.latency_seconds,
        });

        if (autoSaved.length > 0) {
          await loadLibrary();
        }
      } catch {
        setUploadError('Could not reach the server. Check your connection and try again.');
      } finally {
        setUploading(false);
      }
    },
    [loadLibrary]
  );

  const handlePhotoSelected = (uri: string) => {
    setLastPhotoUri(uri);
    setScanSummary(null);
    setAutoSavedCount(0);
    setReviewItems([]);
    runScan(uri);
  };

  const handleRetry = () => {
    if (lastPhotoUri) {
      runScan(lastPhotoUri);
    }
  };

  const handleConfirmItem = async (id: string, title: string, author: string, confidence: number) => {
    setSavingItemId(id);
    try {
      await createBook(title, author, confidence);
      setReviewItems((current) => current.filter((item) => item.id !== id));
      await loadLibrary();
    } catch {
      Alert.alert('Save failed', 'Could not save this book. Please try again.');
    } finally {
      setSavingItemId(null);
    }
  };

  const handleDiscardItem = (id: string) => {
    setReviewItems((current) => current.filter((item) => item.id !== id));
  };

  const showNoBooksMessage = scanSummary !== null && scanSummary.detectionCount === 0;

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.appTitle}>Shelfie</Text>

        <PhotoCapture onPhotoSelected={handlePhotoSelected} disabled={uploading} />

        {uploading && (
          <View style={styles.statusBlock}>
            <ActivityIndicator size="large" color="#2563eb" />
            <Text style={styles.statusText}>Scanning your bookshelf...</Text>
          </View>
        )}

        {uploadError && (
          <View style={styles.statusBlock}>
            <Text style={styles.errorText}>{uploadError}</Text>
            <Pressable style={styles.retryButton} onPress={handleRetry}>
              <Text style={styles.retryButtonText}>Retry</Text>
            </Pressable>
          </View>
        )}

        {showNoBooksMessage && (
          <View style={styles.statusBlock}>
            <Text style={styles.errorText}>
              We couldn't find any books in that photo. Try a clearer, closer shot of the shelf.
            </Text>
          </View>
        )}

        {autoSavedCount > 0 && (
          <View style={styles.statusBlock}>
            <Text style={styles.successText}>
              {autoSavedCount} {autoSavedCount === 1 ? 'book was' : 'books were'} matched with
              high confidence and saved automatically.
            </Text>
          </View>
        )}

        <ReviewQueue
          items={reviewItems}
          savingItemId={savingItemId}
          onConfirm={handleConfirmItem}
          onDiscard={handleDiscardItem}
        />

        <BookList
          books={libraryBooks}
          loading={libraryLoading}
          error={libraryError}
          onRetry={loadLibrary}
        />
      </ScrollView>
      <StatusBar style="auto" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  appTitle: {
    fontSize: 28,
    fontWeight: '800',
    marginBottom: 16,
  },
  statusBlock: {
    marginBottom: 20,
    alignItems: 'flex-start',
    gap: 8,
  },
  statusText: {
    fontSize: 14,
    color: '#475569',
  },
  errorText: {
    fontSize: 14,
    color: '#dc2626',
  },
  successText: {
    fontSize: 14,
    color: '#16a34a',
  },
  retryButton: {
    backgroundColor: '#dc2626',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 6,
  },
  retryButtonText: {
    color: '#ffffff',
    fontWeight: '600',
  },
});
