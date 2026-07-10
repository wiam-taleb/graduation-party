from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# إنشاء ملف قاعدة البيانات محلياً باسم graduation.db
SQLALCHEMY_DATABASE_URL = "postgresql://postgres.mxniybmhgedaslanotkr:WafooRazanWiam@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()