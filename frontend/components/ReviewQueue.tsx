import { StyleSheet, Text, View } from 'react-native';

import ReviewItem from './ReviewItem';
import type { ScanBookResult } from '../services/api';

export interface ReviewQueueItem extends ScanBookResult {
  id: string;
}

interface ReviewQueueProps {
  items: ReviewQueueItem[];
  savingItemId: string | null;
  onConfirm: (id: string, title: string, author: string, confidence: number) => void;
  onDiscard: (id: string) => void;
}

export default function ReviewQueue({ items, savingItemId, onConfirm, onDiscard }: ReviewQueueProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Review Queue ({items.length})</Text>
      <Text style={styles.hint}>
        These books need a quick check before they're added to your shelf.
      </Text>
      {items.map((item) => (
        <ReviewItem
          key={item.id}
          item={item}
          saving={savingItemId === item.id}
          onConfirm={(title, author, confidence) => onConfirm(item.id, title, author, confidence)}
          onDiscard={() => onDiscard(item.id)}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 24,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 4,
  },
  hint: {
    fontSize: 13,
    color: '#64748b',
    marginBottom: 12,
  },
});
