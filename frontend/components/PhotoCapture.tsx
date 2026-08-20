import * as ImagePicker from 'expo-image-picker';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

interface PhotoCaptureProps {
  onPhotoSelected: (uri: string) => void;
  disabled?: boolean;
}

export default function PhotoCapture({ onPhotoSelected, disabled }: PhotoCaptureProps) {
  const handleTakePhoto = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(
        'Camera permission needed',
        'Enable camera access in Settings to take a photo of your bookshelf.'
      );
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ['images'],
      quality: 0.8,
    });

    if (!result.canceled && result.assets.length > 0) {
      onPhotoSelected(result.assets[0].uri);
    }
  };

  const handlePickFromLibrary = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(
        'Photo library permission needed',
        'Enable photo access in Settings to pick a bookshelf photo.'
      );
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.8,
    });

    if (!result.canceled && result.assets.length > 0) {
      onPhotoSelected(result.assets[0].uri);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Scan a Bookshelf</Text>
      <View style={styles.row}>
        <Pressable
          style={[styles.button, disabled && styles.buttonDisabled]}
          onPress={handleTakePhoto}
          disabled={disabled}
        >
          <Text style={styles.buttonText}>Take Photo</Text>
        </Pressable>
        <Pressable
          style={[styles.button, disabled && styles.buttonDisabled]}
          onPress={handlePickFromLibrary}
          disabled={disabled}
        >
          <Text style={styles.buttonText}>Choose from Library</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 20,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
    gap: 10,
  },
  button: {
    flex: 1,
    backgroundColor: '#2563eb',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  buttonDisabled: {
    backgroundColor: '#93c5fd',
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '600',
  },
});
