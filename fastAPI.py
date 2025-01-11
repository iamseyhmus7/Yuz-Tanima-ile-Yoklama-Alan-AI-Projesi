from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from Models.BaseModeller import RegisterUser, LoginUsers, ResetPassword, LessonName
import os
from dotenv import load_dotenv

# Çevresel değişkenleri yükle
load_dotenv()

# Sabitler
SECRET_KEY = "secret-key-for-jwt"
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
    
    def add_lessonName(self, email: str, lesson_name: str):
        existing_lesson = self.collection_lesson.find_one({"email": email, "lesson_name": lesson_name})
        if existing_lesson:
            raise HTTPException(status_code=400, detail="Bu ders zaten eklenmiş.")
        result = self.collection_lesson.insert_one({"email": email, "lesson_name": lesson_name})
        return {"message": "Ders başarıyla eklendi.", "lesson_id": str(result.inserted_id)}

    def delete_lessonName(self, email: str, lesson_name: str):
        result = self.collection_lesson.delete_one({"email": email, "lesson_name": lesson_name})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Bu ders bulunamadı.")
        return {"message": "Ders başarıyla silindi."}

    def get_lessons(self, email: str):
        lessons = list(self.collection_lesson.find({"email": email}, {"_id": 0, "lesson_name": 1}))
        return [lesson["lesson_name"] for lesson in lessons]

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

@app.get("/get_lessons/{email}")
async def get_lessons(email: str):
    lessons = user_service.get_lessons(email)
    return {"lessons": lessons}



@app.post("/register")
async def register_user(data: RegisterUser):
    user_id = user_service.register_user(data.name, data.email, data.password)
    return {"message": "Kayıt başarılı!", "user_id": user_id}

@app.post("/login")
async def login_user(data: LoginUsers):
    token = user_service.login_user(data.email, data.password)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/check-email")
async def check_email(data: ResetPassword):
    user_service.check_email(data.email)
    return {"message": "E-posta bulundu."}

@app.post("/update-password")
async def update_password(data: ResetPassword):
    user_service.update_password(data.email, data.password)
    return {"message": "Şifre başarıyla güncellendi."}

@app.post("/add_lesson")
async def add_lesson(data: LessonName):
    return user_service.add_lessonName(data.email, data.lesson_name)

@app.post("/delete_lesson")
async def delete_lesson(data: LessonName):
    return user_service.delete_lessonName(data.email, data.lesson_name)


