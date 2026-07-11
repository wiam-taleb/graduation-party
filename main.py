from fastapi import FastAPI, Request, Form, UploadFile, File, Depends,APIRouter, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uvicorn
import os
import shutil

import models
from database import SessionLocal, engine

import uuid
from supabase import create_client, Client

import secrets
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import status

security = HTTPBasic()
security = HTTPBasic()


def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    # جلب البيانات من السيرفر فقط، بدون أي قيم افتراضية مكشوفة في الكود
    correct_username = os.getenv("ADMIN_USERNAME")
    correct_password = os.getenv("ADMIN_PASSWORD")

    # حماية إضافية: إذا لم يتم العثور على المتغيرات في Render، نوقف العملية ونمنع الدخول
    if not correct_username or not correct_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطأ في إعدادات الأمان في الخادم. لم يتم العثور على بيانات الاعتماد."
        )

    # التحقق الآمن من مطابقة البيانات المدخلة مع بيانات السيرفر
    is_correct_username = secrets.compare_digest(credentials.username, str(correct_username))
    is_correct_password = secrets.compare_digest(credentials.password, str(correct_password))

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اسم المستخدم أو كلمة المرور غير صحيحة",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
# إنشاء الجداول في قاعدة البيانات إذا لم تكن موجودة
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# التأكد من وجود مجلد حفظ الصور
os.makedirs("static/uploads", exist_ok=True)

# ربط الملفات الثابتة والواجهات
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


# دالة مساعدة لفتح وإغلاق الاتصال بقاعدة البيانات
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# مسار الصفحة الرئيسية (لعرض الموقع)
@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    # جلب الصور التي تم الموافقة عليها فقط
    approved_photos = db.query(models.Photo).filter(models.Photo.is_approved == True).all()
    all_wishes = db.query(models.Wish).all()  # جلب التهاني

    # تمريرها للـ context
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"photos": approved_photos, "wishes": all_wishes}
    )
@app.post("/api/rsvp")
async def submit_rsvp(
    name: str = Form(...),
    phone: str = Form(...),
    attending: bool = Form(...),
    db: Session = Depends(get_db)
):
    try:
        print(f"Received: {name}, {phone}, {attending}") # طباعة البيانات للتأكد من وصولها
        new_rsvp = models.RSVP(name=name, phone=phone, attending=attending)
        db.add(new_rsvp)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        print(f"Error occurred: {e}") # طباعة الخطأ الحقيقي
        return {"status": "error", "message": str(e)}
# API: استقبال رسائل التهنئة
@app.post("/api/wish")
async def submit_wish(
        name: str = Form(...),
        message: str = Form(...),
        db: Session = Depends(get_db)
):
    new_wish = models.Wish(name=name, message=message)
    db.add(new_wish)
    db.commit()
    return {"status": "success"}

@app.post("/api/upload")
async def upload_photo(
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    if not supabase_client:
        return {"status": "error", "message": "لم يتم إعداد روابط Supabase في السيرفر"}

    try:
        # إنشاء اسم عشوائي فريد للصورة لمنع مسح الصور المتشابهة في الاسم
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"

        # قراءة محتوى الصورة
        file_content = await file.read()

        # الرفع المباشر إلى Supabase (حاوية باسم photos)
        supabase_client.storage.from_("photos").upload(
            path=unique_filename,
            file=file_content,
            file_options={"content-type": file.content_type}
        )

        # جلب الرابط العام (Public URL) للصورة من السحابة
        public_url = supabase_client.storage.from_("photos").get_public_url(unique_filename)

        # حفظ الرابط في قاعدة البيانات (استخدمنا حقل filename لتجنب تعديل الجداول)
        new_photo = models.Photo(filename=public_url)
        db.add(new_photo)
        db.commit()

        return {"status": "success", "url": public_url}
    except Exception as e:
        print("Upload Error:", e)
        return {"status": "error", "message": str(e)}

@app.get("/admin")
async def admin_panel(request: Request, db: Session = Depends(get_db), admin: str = Depends(get_current_admin)):
    attendees = db.query(models.RSVP).all()
    wishes = db.query(models.Wish).all()
    photos = db.query(models.Photo).all()

    count = len([a for a in attendees if a.attending])

    color = "yellow"
    if count >= 80:
        color = "red"
    elif count >= 40:
        color = "orange"

    # التعديل الصحيح للنسخ الحديثة من FastAPI:
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "attendees": attendees,
            "wishes": wishes,
            "photos": photos,
            "count": count,
            "color": color
        }
    )
# API: الموافقة على صورة
@app.post("/api/approve-photo/{photo_id}")
async def approve_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.query(models.Photo).filter(models.Photo.id == photo_id).first()
    if photo:
        photo.is_approved = True
        db.commit()
    return {"status": "success"}

# API: حذف صورة أو تهنئة
@app.delete("/api/delete/{type}/{id}")
async def delete_item(type: str, id: int, db: Session = Depends(get_db)):
    # التأكد من تحديد النموذج الصحيح
    model = models.Photo if type == "photo" else models.Wish
    item = db.query(model).filter(model.id == id).first()
    if item:
        db.delete(item)
        db.commit()
        return {"status": "deleted"}
    return {"status": "error", "message": "Item not found"}
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)