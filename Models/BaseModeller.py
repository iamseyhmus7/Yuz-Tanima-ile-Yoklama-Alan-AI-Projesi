from pydantic import BaseModel, EmailStr
from typing import List  # List türünü içe aktarın

# Kullanıcı modeli
class RegisterUser(BaseModel):
   name: str 
   email: EmailStr
   password: str
    
class LoginUsers(BaseModel):
    email : EmailStr
    password : str

class ResetPassword(BaseModel):
    email : EmailStr
    password : str

class CheckEmail(BaseModel):
    email : EmailStr

class StudentModel(BaseModel):
    ad: str
    soyad: str
    ogrenciNo: str
    fotograflar: List[str] # Fotoğrafın base64 formatında olması önerilir
    lesson_name : List[str]  


"""
Yukaridaki sınıflar, özellikle FastAPI gibi framework'lerde, gelen verilerin doğrulanmasını ve yönetilmesini sağlar.
"""