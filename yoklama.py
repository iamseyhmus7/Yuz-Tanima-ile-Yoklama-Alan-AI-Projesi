import cv2
from simple_facerec import SimpleFacerec
from datetime import datetime

def yoklamayaYaz(name):
    with open('yoklama.csv', 'r+') as f:
        myDataList = f.readlines()
        nameList = [entry.split(',')[0] for entry in myDataList]

        if name not in nameList:
            now = datetime.now()
            dtString = now.strftime('%H:%M:%S')
            f.writelines(f'\n{name},{dtString}')

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

        yoklamayaYaz(name)

    cv2.imshow("Frame", frame)

    key = cv2.waitKey(1)
    if key == 27:
        break

cap.release()
cv2.destroyAllWindows()
