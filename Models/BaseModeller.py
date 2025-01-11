from pydantic import BaseModel, EmailStr

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

class LessonName(BaseModel):
    lesson_name : str
    email : EmailStr


"""
Yukaridaki sınıflar, özellikle FastAPI gibi framework'lerde, gelen verilerin doğrulanmasını ve yönetilmesini sağlar.
"""