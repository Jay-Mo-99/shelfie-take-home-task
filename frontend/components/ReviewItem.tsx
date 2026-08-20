import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type { ScanBookResult } from '../services/api';

interface ReviewItemProps {
  item: ScanBookResult;
  saving: boolean;
  onConfirm: (title: string, author: string, confidence: number) => void;
  onDiscard: () => void;
}

export default function ReviewItem({ item, saving, onConfirm, onDiscard }: ReviewItemProps) {
  const suggestedTitle = item.match?.title ?? item.reading.title ?? '';
  const suggestedAuthor = item.match?.author ?? item.reading.author ?? '';

  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(suggestedTitle);
  const [editAuthor, setEditAuthor] = useState(suggestedAuthor);
  const [editConfidence, setEditConfidence] = useState(item.confidence);

  const readingFailed = !item.reading.title && !item.reading.author;
  const canConfirmDirectly = suggestedTitle.trim().length > 0 || suggestedAuthor.trim().length > 0;

  // Candidates are only offered when matching.py could not pick one entry with
  // confidence — tapping one pre-fills the edit form instead of saving blindly.
  const handleUseCandidate = (title: string, author: string, confidence: number) => {
    setEditTitle(title);
    setEditAuthor(author);
    setEditConfidence(confidence);
    setIsEditing(true);
  };

  const handleStartCorrect = () => {
    setEditTitle(suggestedTitle);
    setEditAuthor(suggestedAuthor);
    setEditConfidence(item.confidence);
    setIsEditing(true);
  };

  const handleSaveEdit = () => {
    onConfirm(editTitle.trim(), editAuthor.trim(), editConfidence);
  };

  return (
    <View style={styles.card}>
      {readingFailed ? (
        <Text style={styles.warning}>
          Could not read this spine{item.reading.error ? ` (${item.reading.error})` : ''}.
        </Text>
      ) : (
        <>
          <Text style={styles.detected}>
            Detected: {item.reading.title || 'Unknown title'}
            {item.reading.author ? ` by ${item.reading.author}` : ''}
          </Text>
          {item.match ? (
            <Text style={styles.hint}>
              Closest catalog match: {item.match.title} by {item.match.author} (
              {Math.round(item.confidence * 100)}% confidence)
            </Text>
          ) : item.ambiguous ? (
            <Text style={styles.hint}>Multiple possible matches — pick one below or correct manually.</Text>
          ) : (
            <Text style={styles.hint}>No confident catalog match found.</Text>
          )}
        </>
      )}

      {/* A fully-failed read (e.g. VLM timeout) still produces 0%-confidence
          "candidates" from fuzzy-matching an empty string — those aren't real
          matches, so only offer picks when the VLM actually read something. */}
      {!readingFailed && item.ambiguous && item.candidates.length > 0 && (
        <View style={styles.candidateList}>
          {item.candidates.map((candidate, index) => (
            <Pressable
              key={`${candidate.title}-${index}`}
              style={styles.candidateButton}
              onPress={() => handleUseCandidate(candidate.title, candidate.author, candidate.confidence)}
              disabled={saving}
            >
              <Text style={styles.candidateText}>
                {candidate.title} — {candidate.author} ({Math.round(candidate.confidence * 100)}%)
              </Text>
            </Pressable>
          ))}
        </View>
      )}

      {isEditing ? (
        <View style={styles.editForm}>
          <TextInput
            style={styles.input}
            value={editTitle}
            onChangeText={setEditTitle}
            placeholder="Title"
            editable={!saving}
          />
          <TextInput
            style={styles.input}
            value={editAuthor}
            onChangeText={setEditAuthor}
            placeholder="Author"
            editable={!saving}
          />
          <View style={styles.actionRow}>
            <Pressable style={styles.confirmButton} onPress={handleSaveEdit} disabled={saving}>
              <Text style={styles.actionButtonText}>{saving ? 'Saving...' : 'Save'}</Text>
            </Pressable>
            <Pressable
              style={styles.cancelButton}
              onPress={() => setIsEditing(false)}
              disabled={saving}
            >
              <Text style={styles.actionButtonText}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      ) : (
        <View style={styles.actionRow}>
          <Pressable
            style={[styles.confirmButton, !canConfirmDirectly && styles.buttonDisabled]}
            onPress={() => onConfirm(suggestedTitle, suggestedAuthor, item.confidence)}
            disabled={!canConfirmDirectly || saving}
          >
            <Text style={styles.actionButtonText}>Confirm</Text>
          </Pressable>
          <Pressable style={styles.correctButton} onPress={handleStartCorrect} disabled={saving}>
            <Text style={styles.actionButtonText}>Correct</Text>
          </Pressable>
          <Pressable style={styles.discardButton} onPress={onDiscard} disabled={saving}>
            <Text style={styles.actionButtonText}>Discard</Text>
          </Pressable>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#f8fafc',
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  detected: {
    fontSize: 15,
    fontWeight: '600',
    marginBottom: 4,
  },
  hint: {
    fontSize: 13,
    color: '#475569',
    marginBottom: 8,
  },
  warning: {
    fontSize: 14,
    color: '#b45309',
    marginBottom: 8,
  },
  candidateList: {
    marginBottom: 8,
    gap: 6,
  },
  candidateButton: {
    backgroundColor: '#e0e7ff',
    borderRadius: 6,
    paddingVertical: 8,
    paddingHorizontal: 10,
  },
  candidateText: {
    color: '#3730a3',
    fontSize: 13,
  },
  editForm: {
    gap: 8,
    marginBottom: 4,
  },
  input: {
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 6,
    paddingVertical: 8,
    paddingHorizontal: 10,
    backgroundColor: '#ffffff',
    fontSize: 14,
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 4,
  },
  confirmButton: {
    flex: 1,
    backgroundColor: '#16a34a',
    paddingVertical: 10,
    borderRadius: 6,
    alignItems: 'center',
  },
  correctButton: {
    flex: 1,
    backgroundColor: '#2563eb',
    paddingVertical: 10,
    borderRadius: 6,
    alignItems: 'center',
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#64748b',
    paddingVertical: 10,
    borderRadius: 6,
    alignItems: 'center',
  },
  discardButton: {
    flex: 1,
    backgroundColor: '#dc2626',
    paddingVertical: 10,
    borderRadius: 6,
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  actionButtonText: {
    color: '#ffffff',
    fontWeight: '600',
    fontSize: 13,
  },
});
