import face_recognition
import cv2
import os
import glob
import numpy as np

class SimpleFacerec:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []

        # Daha hızlı bir hız için çerçeveyi yeniden boyutlandırın
        self.frame_resizing = 0.25

    def load_encoding_images(self, images_root_path):
        img_folders = os.listdir(images_root_path)

        for folder_name in img_folders:
            folder_path = os.path.join(images_root_path, folder_name)
            if not os.path.isdir(folder_path):
                continue

            images_path = glob.glob(os.path.join(folder_path, "*.*"))

            print(f"{len(images_path)} encoding images found for {folder_name}.")

            for img_path in images_path:
                img = cv2.imread(img_path)
                if img is None:
                    print(f"Cannot read image: {img_path}")
                    continue
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                # Dosya adını yalnızca dosya yolundan alın.
                filename = os.path.splitext(os.path.basename(img_path))[0]

                # Yüz kodlamasını al
                face_encodings = face_recognition.face_encodings(rgb_img)
                if len(face_encodings) > 0:
                    img_encoding = face_encodings[0]
                else:
                    continue

                # Dosya adını ve kodlamayı saklayın
                self.known_face_encodings.append(img_encoding)
                self.known_face_names.append(folder_name)

        print("Encoding images loaded")

    def detect_known_faces(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            # Yüzün bilinen yüzlerle eşleşip eşleşmediğine bakın
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"

            # Eşleşme varsa, en yakın eşleşmeyi bulun
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = self.known_face_names[best_match_index]

            face_names.append(name)

        # Yüz konumlarını yeniden boyutlandırarak ayarlayın
        face_locations = np.array(face_locations)
        face_locations = face_locations / self.frame_resizing
        return face_locations.astype(int), face_names
