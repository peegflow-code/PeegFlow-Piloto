from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    users = relationship("User", back_populates="company")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")  # admin | user
    company_id = Column(Integer, ForeignKey("companies.id"))

    company = relationship("Company", back_populates="users")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer)
    name = Column(String)
    sku = Column(String)
    price_retail = Column(Float)
    price_wholesale = Column(Float)
    stock = Column(Integer, default=0)
    stock_min = Column(Integer, default=5)


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer)
    product_id = Column(Integer)
    quantity = Column(Integer)
    price = Column(Float)
    user_id = Column(Integer)
    date = Column(DateTime, default=datetime.utcnow)


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer)
    description = Column(String)
    category = Column(String)
    amount = Column(Float)
    date = Column(DateTime)
