from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# =========================================================
# EMPRESAS (TENANTS)
# =========================================================

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    license_key = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="company", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="company", cascade="all, delete-orphan")

# =========================================================
# USUÁRIOS
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")  # admin / user

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    company = relationship("Company", back_populates="users")

    __table_args__ = (
        UniqueConstraint("company_id", "username", name="uq_user_company"),
        Index("idx_user_company", "company_id"),
    )

# =========================================================
# PRODUTOS
# =========================================================

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    sku = Column(String, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="Geral")
    price_retail = Column(Float, nullable=False)
    price_wholesale = Column(Float, nullable=True)
    stock = Column(Integer, default=0)
    stock_min = Column(Integer, default=5)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    company = relationship("Company", back_populates="products")

    __table_args__ = (
        Index("idx_product_company", "company_id"),
        UniqueConstraint("company_id", "sku", name="uq_product_company_sku"),
    )

# =========================================================
# VENDAS
# =========================================================

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    kind = Column(String, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    __table_args__ = (
        Index("idx_sale_company", "company_id"),
        Index("idx_sale_date", "date"),
    )

# =========================================================
# DESPESAS
# =========================================================

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)

    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    company = relationship("Company", back_populates="expenses")

    __table_args__ = (
        Index("idx_expense_company", "company_id"),
        Index("idx_expense_date", "date"),
    )
