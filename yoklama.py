import cv2
from simple_facerec import SimpleFacerec
from datetime import datetime
import json 

def yoklama(name):
    #Json Olarak Okuma
    try:
        with open("yoklama.json","r") as json_file:
            data = json.load(json_file)   # json_file nesnesinden JSON verilerini okuyarak Python veri yapısına (liste veya sözlük) dönüştürür ve data değişkenine atar.



    except FileNotFoundError:
        data = [] # Eğer dosya yoksa , boş bir liste döndür.
    

    # İsimler listesi oluştur
    name_list = [entry["name"] for entry in data] # Mevcut verilerden (yani data listesindeki her kayıt) sadece isimleri alarak yeni bir liste oluşturur.
                                                  # Bu liste, eklenmemiş isimleri kontrol etmek için kullanılacaktır.



    # Eğer isim yoksa, yeni kayıt ekle
    if name not in name_list:
        now = datetime.now()
        dtString = now.strftime('%H:%M:%S') # Şimdiki zamanı alır ve string formatına çevirir.


        # Yeni kayıt oluştur
        entry = {"name":name ,
                  "zaman" : dtString}
        data.append(entry)


        #Json Dosyasına yaz
        with open("yoklama.json" , "w") as file:
            json.dump(data , file , indent=4) # indent=4 parametresi, dosyanın daha okunabilir olmasını sağlamak için her seviyeyi 4 boşluk ile girintiler.
            


# SimpleFacerec sınıfından bir örnek oluşturun
sfr = SimpleFacerec()

sfr.load_encoding_images("images/")  # Buradaki "images/" kısmını kendi klasör yapınıza göre ayarlayın

# Kamerayı Yükle
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()

    # Yüzleri Algıla
    face_locations, face_names = sfr.detect_known_faces(frame)

    for face_loc, name in zip(face_locations, face_names):
        y1, x2, y2, x1 = face_loc[0], face_loc[1], face_loc[2], face_loc[3]

        cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 200), 2)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 4)

        yoklama(name)

    cv2.imshow("Frame", frame)

    key = cv2.waitKey(1)
    if key == 27:
        break

cap.release()
cv2.destroyAllWindows()
