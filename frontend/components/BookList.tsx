import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Book } from '../services/api';

interface BookListProps {
  books: Book[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export default function BookList({ books, loading, error, onRetry }: BookListProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>My Shelf ({books.length})</Text>

      {loading && <Text style={styles.hint}>Loading your library...</Text>}

      {error && (
        <View style={styles.errorRow}>
          <Text style={styles.errorText}>{error}</Text>
          <Pressable style={styles.retryButton} onPress={onRetry}>
            <Text style={styles.retryButtonText}>Retry</Text>
          </Pressable>
        </View>
      )}

      {!loading && !error && books.length === 0 && (
        <Text style={styles.hint}>No books saved yet. Scan a shelf to get started.</Text>
      )}

      {books.map((book) => (
        <View key={book.id} style={styles.row}>
          <Text style={styles.bookTitle}>{book.title}</Text>
          <Text style={styles.bookAuthor}>{book.author}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 20,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  hint: {
    fontSize: 13,
    color: '#64748b',
  },
  errorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  errorText: {
    color: '#dc2626',
    fontSize: 13,
    flexShrink: 1,
  },
  retryButton: {
    backgroundColor: '#dc2626',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
  },
  retryButtonText: {
    color: '#ffffff',
    fontWeight: '600',
    fontSize: 12,
  },
  row: {
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    paddingVertical: 8,
  },
  bookTitle: {
    fontSize: 15,
    fontWeight: '600',
  },
  bookAuthor: {
    fontSize: 13,
    color: '#475569',
  },
});
