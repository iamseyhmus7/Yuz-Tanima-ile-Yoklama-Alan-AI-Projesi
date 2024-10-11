import cv2
import json
import time
from datetime import datetime
from simple_facerec import SimpleFacerec



# Yoklama fonksiyonu
def yoklama(name):
    try:
        with open("yoklama.json", "r") as json_file:
            data = json.load(json_file)
    except FileNotFoundError:
        data = []
    
    name_list = [entry["name"] for entry in data]
    
    if name not in name_list:
        now = datetime.now()
        dtString = now.strftime('%d,%m, %A %H:%M:%S')
        entry = {"name": name, "zaman": dtString}
        data.append(entry)

        with open("yoklama.json", "w") as file:
            json.dump(data, file, indent=4)

# Ana program
if __name__ == "__main__":
    # SimpleFacerec sınıfını başlatın ve kodlamaları yükleyin
    sfr = SimpleFacerec()
    sfr.load_and_train_model("images/", "face_encodings.pkl")

    # Kodlamaları yükle
    sfr.load_encoding_images("face_encodings.pkl")  # Daha önce eğitilmiş kodlamaları yükle

    # Kamerayı başlat
    cap = cv2.VideoCapture(0)


    # Kamera Çözünürlüğünü arttırma 
    cap.set(cv2.CAP_PROP_FRAME_WIDTH , 1280) # Genişlik
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT , 720) # Yükseklik

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Kamera görüntüsü alinamiyor!")
            break


        # Görüntüyü histogram eşitlemesi ile işleme
        preprocessed_frame = sfr.preprocess_frame(frame)
        face_locations, face_names = sfr.detect_known_faces(preprocessed_frame)


        # Yüzleri algıla ve tanı
        face_locations, face_names = sfr.detect_known_faces(frame)        
        for face_loc, name in zip(face_locations, face_names):
            y1, x2, y2, x1 = face_loc[0], face_loc[1], face_loc[2], face_loc[3]
            cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 200), 2)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 4)

            # Yoklama işlemi
            yoklama(name)

        cv2.imshow("Yüz Tanima", frame)

        # ESC tuşuna basılırsa kamerayı durdur
        if cv2.waitKey(1) & 0xFF == 27:
            break

        time.sleep(0.5) # Her çerçeve arasında 0.5 salise bekleme süresi 

    # Kamera serbest bırakılır ve pencereler kapatılır
    cap.release()
    cv2.destroyAllWindows()
    print("Yüz tanima işlemi tamamlandi.")
