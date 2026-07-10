from fastapi import FastAPI, Request, Form, UploadFile, File, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uvicorn
import os
import shutil

import models
from database import SessionLocal, engine

# إنشاء الجداول في قاعدة البيانات إذا لم تكن موجودة
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# التأكد من وجود مجلد حفظ الصور
os.makedirs("static/uploads", exist_ok=True)

# ربط الملفات الثابتة والواجهات
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


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


# API: استقبال ورفع الصور من الضيوف
@app.post("/api/upload")
async def upload_photo(
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    # حفظ الملف في مجلد uploads
    file_location = f"static/uploads/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # حفظ اسم الصورة في قاعدة البيانات (مع جعل is_approved=False)
    new_photo = models.Photo(filename=file.filename)
    db.add(new_photo)
    db.commit()

    return {"status": "success", "filename": file.filename}


@app.get("/admin")
async def admin_panel(request: Request, db: Session = Depends(get_db)):
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