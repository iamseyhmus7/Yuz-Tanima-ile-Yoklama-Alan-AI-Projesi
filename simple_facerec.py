import face_recognition
import cv2
import os
import glob
import pickle
import numpy as np

class SimpleFacerec:
    def __init__(self):
        self.known_face_encodings = [] # known_face_encodings: Tanınmış yüzlerin kodlamalarını saklamak için bir liste.
        self.known_face_names = []  # known_face_names: Tanınmış yüzlerin isimlerini saklamak için bir liste.
        self.frame_resizing = 0.75  # Daha hızlı bir hız için çerçeveyi yeniden boyutlandır

    
    # Histogram eşitlemesi ile görüntüyü işleme fonksiyonu 
    def preprocess_frame(self , frame):
        # Histogram eşitlemesi ile yüzlerin daha belirgin hale getirilmesi
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Önce gri tonlamaya dönüştürülür
        equalized = cv2.equalizeHist(gray)  # Gri tonlamalı görüntüye histogram eşitlemesi yapılır
        return equalized  # Renkli formata geri dönüştürülmez, gri tonlamalı olarak devam eder
    

    # Yüz Modeli Yükleme ve Eğitim Metodu
    def load_and_train_model(self, images_root_path, encoding_file_path): # images_root_path: Yüz görüntülerinin bulunduğu ana dizin yolu , # encoding_file_path: Kodlamaların kaydedileceği dosya yolu.
        known_face_encodings = []
        known_face_names = []

        img_folders = os.listdir(images_root_path) # os.listdir(images_root_path): Belirtilen dizindeki dosya ve klasörlerin listesini alır.
        
        # Her Klasörü Dolaşma ve Yüz Görüntülerini Yükleme
        for folder_name in img_folders:
            folder_path = os.path.join(images_root_path, folder_name)
            if not os.path.isdir(folder_path):
                continue

        # Klasör İçindeki Görüntüleri Bulma
            images_path = glob.glob(os.path.join(folder_path, "*.*"))

            for img_path in images_path:
                img = face_recognition.load_image_file(img_path)

                # Yüz kodlamasını al
                face_encodings = face_recognition.face_encodings(img)
                if len(face_encodings) > 0: # Eğer kodlama alınabilmişse, kodlama dizisinin ilk elemanı alınır ve iki listeye eklenir.
                    img_encoding = face_encodings[0]
                    known_face_encodings.append(img_encoding)
                    known_face_names.append(folder_name)

        # Kodlamaları kaydet
        with open(encoding_file_path, 'wb') as f:  # 'wb' modunda açarak yazma işlemi yaptık
            pickle.dump((known_face_encodings, known_face_names), f)
            print(f"Model eğitildi ve {len(known_face_encodings)} kodlama kaydedildi.")
    
    

    # Yüz Kodlamalarını Yükleme Metodu
    def load_encoding_images(self, encoding_file_path): # encoding_file_path: Yüz kodlamalarının kaydedildiği dosya yolu.
        try:
            with open(encoding_file_path, 'rb') as f:
                self.known_face_encodings, self.known_face_names = pickle.load(f) # pickle.load: Kodlamaları ve isimleri dosyadan yükler.
            print("Kodlamalar yüklendi.")
        except FileNotFoundError:
            print("Kodlama dosyası bulunamadı. Lütfen modeli önce eğitin.")

    

    # Tanınmış Yüzleri Algılama Metodu
    def detect_known_faces(self, frame):
        # Çerçeveyi yeniden boyutlandırın ve RGB formatına çevirin
        small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing) # cv2.resize: Görüntüyü yeniden boyutlandırır.
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB) # cv2.cvtColor: Görüntüyü RGB formatına çevirir.

        # Yüzleri algılayın
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        
        for face_encoding in face_encodings:
            # Yüzün bilinen yüzlerle eşleşip eşleşmediğine bakın
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Taninamadi"

            # Eşleşme varsa, en yakın eşleşmeyi bulun
            if True in matches:
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding) # face_distances: Yüzlerin benzerliğini ölçmek için kullanılır.
                best_match_index = np.argmin(face_distances) # best_match_index: En yakın eşleşmenin indeksini bulur.
                if matches[best_match_index] and face_distances[best_match_index] <0.5:
                    name = self.known_face_names[best_match_index] # face_locations ve face_names döndürülerek, algılanan yüzlerin konumları ve isimleri geri gönderilir.

            face_names.append(name)

        # Yüz konumlarını yeniden boyutlandırarak ayarlayın
        face_locations = np.array(face_locations)
        face_locations = face_locations / self.frame_resizing
        return face_locations.astype(int), face_names
