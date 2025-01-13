import pickle
import base64
import face_recognition
from fastapi import FastAPI, HTTPException, Depends, Query, Body
from Models.BaseModeller import RegisterUser, LoginUsers, ResetPassword, CheckEmail, StudentModel
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from io import BytesIO
import os
import logging

# Çevresel değişkenleri yükle
load_dotenv()

# Sabitler
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 50

# Şifreleme ve OAuth2 ayarları
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# MongoDB bağlantı sınıfı
class MongoDB:
    def __init__(self, uri, db_name, collection_names):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collections = {name: self.db[name] for name in collection_names}

# JWT yardımcı sınıfı
class JWTUtility:
    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta = None):
        """
        JSON Web Token oluşturur.
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def verify_token(token: str):
        """
        Token doğrulama işlemi.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload.get("sub")
        except JWTError:
            return None

# Şifre yardımcı sınıfı
class PasswordUtility:
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Şifreyi hash'ler.
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Şifre doğrulama.
        """
        return pwd_context.verify(plain_password, hashed_password)

# Kullanıcı servisi sınıfı
class UserService:
    def __init__(self, db):
        self.collection = db["OgretmenBilgileri"]
        self.collection_lesson = db["DersName"]

    def register_user(self, name: str, email: str, password: str):
        """
        Yeni kullanıcı kaydı.
        """
        if self.collection.find_one({"email": email}):
            raise HTTPException(status_code=400, detail="Bu e-posta zaten kayıtlı.")
        hashed_password = PasswordUtility.hash_password(password)
        result = self.collection.insert_one({"name": name, "email": email, "password": hashed_password})
        return str(result.inserted_id)

    def login_user(self, email: str, password: str):
        """
        Kullanıcı girişi ve token oluşturma.
        """
        user = self.collection.find_one({"email": email})
        if not user or not PasswordUtility.verify_password(password, user["password"]):
            raise HTTPException(status_code=401, detail="Geçersiz e-posta veya şifre.")
        return JWTUtility.create_access_token({"sub": email})

    def check_email(self, email: str):
        """
        E-posta kontrolü.
        """
        if not self.collection.find_one({"email": email}):
            raise HTTPException(status_code=404, detail="Bu e-postayla kayıtlı kullanıcı bulunamadı.")
        return True

    def update_password(self, email: str, new_password: str):
        """
        Şifre güncelleme.
        """
        hashed_password = PasswordUtility.hash_password(new_password)
        result = self.collection.update_one({"email": email}, {"$set": {"password": hashed_password}})
        if result.modified_count != 1:
            raise HTTPException(status_code=404, detail="E-posta bulunamadı.")
        return True

    def get_lessons_by_teacher(self, teacher_email: str):
        """
        Öğretmene ait dersleri getir.
        """
        lessons = list(self.collection_lesson.find({"email": teacher_email}, {"_id": 0, "lesson_name": 1}))
        return lessons

# Yüz tanıma servisi sınıfı
class FaceRecognitionService:
    def __init__(self, db):
        self.db = db
        with open("face_encodings.pkl", "rb") as file:
            self.known_face_encodings = pickle.load(file)

    def detect_students(self, image_data):
        """
        Görüntü üzerinden öğrencileri tespit et.
        """
        try:
            if isinstance(image_data, str) and image_data.startswith("data:image"):
                image_data = base64.b64decode(image_data.split(",")[1])

            image = face_recognition.load_image_file(BytesIO(image_data))
            face_encodings = face_recognition.face_encodings(image)

            detected_students = []
            students = list(self.db["OgrenciBilgileri"].find({}, {"ad": 1, "soyad": 1, "fotograflar": 1, "lesson_name": 1}))

            for face_encoding in face_encodings:
                best_match = None
                best_distance = float('inf')

                for student in students:
                    for photo in student.get("fotograflar", []):
                        photo_data = base64.b64decode(photo.split(",")[1])
                        photo_image = face_recognition.load_image_file(BytesIO(photo_data))
                        photo_encodings = face_recognition.face_encodings(photo_image)

                        if not photo_encodings:
                            continue

                        distance = face_recognition.face_distance([photo_encodings[0]], face_encoding)[0]
                        if distance < best_distance:
                            best_distance = distance
                            best_match = student

                if best_match:
                    detected_students.append(best_match)

            return detected_students
        except Exception as e:
            logging.error(f"Yüz tanıma sırasında hata: {str(e)}")
            raise

    def process_attendance(self, lesson_name, detected_students):
        """
        Yoklama işlemi.
        """
        try:
            # Ders bilgilerini getir
            lesson = self.db["DersName"].find_one({"lesson_name": lesson_name})
            if not lesson:
                logging.error(f"Ders bulunamadı: {lesson_name}")
                raise HTTPException(status_code=404, detail="Ders bulunamadı.")

            # Bu derse kayıtlı öğrencileri getir
            registered_students = list(self.db["OgrenciBilgileri"].find(
                {"lesson_name": lesson_name},  # Öğrencinin ders listesinde bu dersin olup olmadığını kontrol et
                {"ad": 1, "soyad": 1, "ogrenciNo": 1}
            ))
            logging.info(f"Kayıtlı öğrenciler: {registered_students}")

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Her kayıtlı öğrenci için yoklama durumu belirle
            for student in registered_students:
                full_name = f"{student['ad']} {student['soyad']}"
                ogrenciNo = student["ogrenciNo"]
                status = "Var" if any(full_name == f"{s['ad']} {s['soyad']}" for s in detected_students) else "Yok"
                logging.info(f"Yoklama kaydı: {full_name} ({ogrenciNo}), Durum: {status}")

                # Yeni yoklama kaydı ekle
                self.db["YoklamaVeritabani"].insert_one({
                    "lesson_name": lesson_name,
                    "student_name": full_name,
                    "ogrenciNo": ogrenciNo,
                    "date": now,
                    "status": status
                })
                logging.info(f"Kayıt başarıyla eklendi: {full_name}, Durum: {status}")
        except Exception as e:
            logging.error(f"Yoklama işlemi sırasında hata: {str(e)}")
            raise


# FastAPI uygulaması
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# MongoDB başlatma
mongo_db = MongoDB(
    uri=os.getenv("MONGO_CLIENT"),
    db_name=os.getenv("DATABASE_NAME"),
    collection_names=[name.strip() for name in os.getenv("COLLECTION_NAMES", "").split(",") if name.strip()]
)

user_service = UserService(mongo_db.collections)
face_service = FaceRecognitionService(mongo_db.collections)  # Yüz tanıma servisini başlat

# Endpointler
@app.get("/", response_class=HTMLResponse)
async def login_page():
    """
    Login sayfasını döndür.
    """
    return FileResponse("static/login.html")

@app.get("/get_register", response_class=HTMLResponse)
async def register_page():
    """
    Kayıt sayfasını döndür.
    """
    return FileResponse("static/register.html")

@app.get("/sifreyenileme", response_class=HTMLResponse)
async def reset_page():
    """
    Şifre yenileme sayfasını döndür.
    """
    return FileResponse("static/sifreGuncelleme.html")

@app.get("/arayuz", response_class=HTMLResponse)
async def dashboard():
    """
    Öğretmen paneli.
    """
    return FileResponse("static/arayuz.html")

@app.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    """
    Korunan bir endpoint.
    """
    email = JWTUtility.verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Geçersiz kimlik bilgileri.")
    return {"message": "Bu korunan bir endpointtir!", "email": email}

@app.get("/lessons")
async def get_lessons(teacher_email: str = Query(...)):
    """
    Belirtilen öğretmene ait dersleri getir.
    """
    lessons = user_service.get_lessons_by_teacher(teacher_email)
    if not lessons:
        raise HTTPException(status_code=404, detail="Bu öğretmen için ders bulunamadı.")
    return lessons

@app.get("/attendance-results")
async def get_attendance_results(lesson_name: str = Query(...)):
    """
    Yoklama sonuçlarını döndür.
    """
    results = list(mongo_db.collections["YoklamaVeritabani"].find(
        {"lesson_name": lesson_name}, 
        {"_id": 0, "student_name": 1, "ogrenciNo": 1, "date": 1, "status": 1}
    ))
    if not results:
        logging.info(f"No results found for lesson_name: {lesson_name}")
        raise HTTPException(status_code=404, detail="Yoklama sonuçları bulunamadı.")
    return results

@app.post("/register")
async def register_user(data: RegisterUser):
    """
    Yeni kullanıcı kaydı.
    """
    user_id = user_service.register_user(data.name, data.email, data.password)
    return {"message": "Kayıt başarılı!", "user_id": user_id}

@app.post("/login")
async def login_user(data: LoginUsers):
    """
    Kullanıcı girişi.
    """
    token = user_service.login_user(data.email, data.password)
    return {"access_token": token, "token_type": "bearer", "email": data.email}

@app.post("/check-email")
async def check_email(data: CheckEmail):
    """
    E-posta kontrolü.
    """
    user_service.check_email(data.email)
    return {"message": "E-posta bulundu."}

@app.post("/update-password")
async def update_password(data: ResetPassword):
    """
    Şifre güncelleme işlemi.
    """
    user_service.update_password(data.email, data.password)
    return {"message": "Şifre başarıyla güncellendi."}

@app.post("/attendance")
async def process_attendance(lesson_name: str = Body(...), image: str = Body(...)):
    """
    Yoklama işlemini başlat.
    """
    try:
        image_data = base64.b64decode(image.split(",")[1])
        detected_students = face_service.detect_students(image_data)
        face_service.process_attendance(lesson_name, detected_students)
        return {"message": "Katılım başarıyla kaydedildi."}
    except IndexError:
        raise HTTPException(status_code=400, detail="Görsel verisi uygun formatta değil.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Beklenmeyen bir hata oluştu: {str(e)}")
