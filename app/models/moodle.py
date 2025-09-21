# app/models/moodle.py
from sqlalchemy import Column, BigInteger, Numeric, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from app.db.base_class import Base

Base = declarative_base()

class MdlGradeGrades(Base):
    __tablename__ = 'mdl_grade_grades'
    id = Column(BigInteger, primary_key=True, index=True)
    itemid = Column(BigInteger, index=True)
    userid = Column(BigInteger, index=True)
    finalgrade = Column(Numeric(10, 5))
    timemodified = Column(BigInteger)

class MdlGradeItems(Base):
    __tablename__ = 'mdl_grade_items'
    id = Column(BigInteger, primary_key=True, index=True)
    courseid = Column(BigInteger, index=True)
    itemname = Column(String(255))
    itemtype = Column(String(255))
    gradepass = Column(Numeric(10, 5), default=0.0)


class MdlUser(Base):
    __tablename__ = 'mdl_user'
    id = Column(BigInteger, primary_key=True, index=True)
    firstname = Column(String(100))
    lastname = Column(String(100))
    email = Column(String(100), unique=True)

class MdlCourse(Base):
    __tablename__ = 'mdl_course'
    id = Column(BigInteger, primary_key=True, index=True)
    fullname = Column(String(254))
    shortname = Column(String(255))
    category = Column(BigInteger, nullable=True, index=True)
    
class MdlCourseCategories(Base):
    __tablename__ = 'mdl_course_categories'

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
