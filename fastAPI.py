from fastapi import FastAPI, HTTPException, Depends, Query , Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from Models.BaseModeller import RegisterUser, LoginUsers, ResetPassword , CheckEmail
import os
from dotenv import load_dotenv
from fastapi import UploadFile
import base64
from io import BytesIO
from PIL import Image

# Çevresel değişkenleri yükle
load_dotenv()

# Sabitler
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 50

# Şifreleme ve OAuth2 girişimlerini başlat
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# MongoDB bağlantısı için sınıf
class MongoDB:
    def __init__(self, uri, db_name, collection_names):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.collections = {name: self.db[name] for name in collection_names}

# JWT yardımcı sınıfı
class JWTUtility:
    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def verify_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload.get("sub")
        except JWTError:
            return None

# Şifreleme yardımcı sınıfı
class PasswordUtility:
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

# Kullanıcı işlemleri için servis sınıfı
class UserService:
    def __init__(self, db):
        self.collection = db["OgretmenBilgileri"]
        self.collection_lesson = db["DersName"]

    def register_user(self, name: str, email: str, password: str):
        if self.collection.find_one({"email": email}):
            raise HTTPException(status_code=400, detail="Bu email ile kullanıcı zaten mevcut.")
        hashed_password = PasswordUtility.hash_password(password)
        result = self.collection.insert_one({"name": name, "email": email, "password": hashed_password})
        return str(result.inserted_id)

    def login_user(self, email: str, password: str):
        user = self.collection.find_one({"email": email})
        if not user or not PasswordUtility.verify_password(password, user["password"]):
            raise HTTPException(status_code=401, detail="Geçersiz email veya şifre.")
        return JWTUtility.create_access_token({"sub": email})

    def check_email(self, email: str):
        if not self.collection.find_one({"email": email}):
            raise HTTPException(status_code=404, detail="Bu e-posta ile kullanıcı bulunamadı.")
        return True

    def update_password(self, email: str, new_password: str):
        hashed_password = PasswordUtility.hash_password(new_password)
        result = self.collection.update_one({"email": email}, {"$set": {"password": hashed_password}})
        if result.modified_count != 1:
            raise HTTPException(status_code=404, detail="E-posta bulunamadı.")
        return True
    
    def get_lessons_by_teacher(self, teacher_email: str):
        lessons = list(self.collection_lesson.find({"email": teacher_email}, {"_id": 0, "lesson_name": 1}))
        return lessons


# Yüz tanıma modeli entegrasyonu için fonksiyon
def run_face_recognition(image, students):
    # Bu fonksiyon algılanan yüzleri fotoğraflarla karşılaştıracak
    detected_students = []
    for student in students:
        for photo in student.get("fotograflar", []):
            # Fotoğrafları karşılaştırın (modelinizi kullanarak)
            # Ornek: eğer model algılama yaparsa
            if photo == "match":  # Bu kısmı kendi model fonksiyonunuza bağlı yapın
                detected_students.append(student)
                break
    return detected_students


# FastAPI uygulaması
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# MongoDB bağlantısını başlat
mongo_db = MongoDB(
    uri=os.getenv("MONGO_CLIENT"),
    db_name=os.getenv("DATABASE_NAME"),
    collection_names=[name.strip() for name in os.getenv("COLLECTION_NAMES", "").split(",") if name.strip()]
)

user_service = UserService(mongo_db.collections)

# Endpoints
@app.get("/", response_class=HTMLResponse)
async def login_page():
    return FileResponse("static/login.html")

@app.get("/get_register", response_class=HTMLResponse)
async def register_page():
    return FileResponse("static/register.html")

@app.get("/sifreyenileme", response_class=HTMLResponse)
async def reset_page():
    return FileResponse("static/sifreGuncelleme.html")

@app.get("/arayuz", response_class=HTMLResponse)
async def dashboard():
    return FileResponse("static/arayuz.html")

@app.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    email = JWTUtility.verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Geçersiz kimlik bilgileri.")
    return {"message": "Bu, korunan bir endpointtir!", "email": email}

@app.get("/lessons")
async def get_lessons(teacher_email: str = Query(...)):
    """
    Öğretmenin e-posta adresine göre dersleri döndür.
    """
    lessons = user_service.get_lessons_by_teacher(teacher_email)
    if not lessons:
        raise HTTPException(status_code=404, detail="Bu öğretmen için ders bulunamadı.")
    return lessons


@app.post("/register")
async def register_user(data: RegisterUser):
    user_id = user_service.register_user(data.name, data.email, data.password)
    return {"message": "Kayıt başarılı!", "user_id": user_id}

@app.post("/login")
async def login_user(data: LoginUsers):
    token = user_service.login_user(data.email, data.password)
    return {"access_token": token, "token_type": "bearer", "email": data.email}

@app.post("/check-email")
async def check_email(data: CheckEmail):
    user_service.check_email(data.email)
    return {"message": "E-posta bulundu."}

@app.post("/update-password")
async def update_password(data: ResetPassword):
    user_service.update_password(data.email, data.password)
    return {"message": "Şifre başarıyla güncellendi."}

@app.post("/attendance")
async def process_attendance(lesson_name: str = Body(...), image: str = Body(...)):
    image_data = base64.b64decode(image.split(",")[1])
    image = Image.open(BytesIO(image_data))

    # Tüm öğrencilerı koleksiyondan al
    students = list(mongo_db.collections["OgrenciBilgileri"].find({}, {"_id": 0, "ad": 1, "soyad": 1, "ogrenciNo": 1, "fotograflar": 1}))

    detected_students = run_face_recognition(image, students)

    now = datetime.now()

    for student in students:
        is_detected = any(s["ogrenciNo"] == student["ogrenciNo"] for s in detected_students)
        status = "True" if is_detected else "False"
        mongo_db.collections["YoklamaVeritabani"].insert_one({
            "lesson_name": lesson_name,
            "student_name": f"{student['ad']} {student['soyad']}",
            "ogrenciNo": student["ogrenciNo"],
            "date": now.strftime("%Y-%m-%d %H:%M:%S"),
            "status": status
        })

    return {"message": "Yoklama başarıyla kaydedildi."}