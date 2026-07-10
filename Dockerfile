# استخدام نسخة بايثون خفيفة
FROM python:3.9

# إعداد مجلد العمل داخل الحاوية
WORKDIR /code

# نسخ ملف المتطلبات أولاً لتسريع عملية البناء
COPY ./requirements.txt /code/requirements.txt

# تثبيت المكتبات
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# نسخ باقي ملفات المشروع
COPY . /code

# تشغيل التطبيق باستخدام uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]