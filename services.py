# services.py
import bcrypt
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, Product, Sale, Expense, Company

# =========================
# 🔐 SEGURANÇA / USUÁRIOS
# =========================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def authenticate(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None

def create_initial_data(db: Session):
    if not db.query(Company).filter_by(id=1).first():
        company = Company(id=1, name="Empresa Principal", license_key="MASTER")
        db.add(company)
        db.commit()

    if not db.query(User).filter_by(username="admin").first():
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            company_id=1
        )
        db.add(admin)
        db.commit()

# =========================
# 📦 PRODUTOS / ESTOQUE
# =========================

def get_products(db: Session, company_id: int):
    return db.query(Product).filter(Product.company_id == company_id).all()

def register_product(db: Session, company_id: int, name, price_retail, price_wholesale, stock_min, sku):
    prod = Product(
        name=name,
        price_retail=price_retail,
        price_wholesale=price_wholesale,
        stock=0,
        stock_min=stock_min,
        sku=sku,
        company_id=company_id
    )
    db.add(prod)
    db.commit()

def delete_product(db: Session, product_id: int, company_id: int):
    prod = db.query(Product).filter_by(id=product_id, company_id=company_id).first()
    if prod:
        db.delete(prod)
        db.commit()

def restock_product(db: Session, company_id: int, product_id: int, qty: int, cost_unit: float):
    product = db.query(Product).filter_by(id=product_id, company_id=company_id).first()
    if not product:
        return False

    product.stock += qty

    expense = Expense(
        description=f"Reposição {product.name}",
        amount=qty * cost_unit,
        category="CMV",
        company_id=company_id,
        date=datetime.now()
    )
    db.add(expense)
    db.commit()
    return True

# =========================
# 🛒 VENDAS / PDV
# =========================

def process_sale(db: Session, product_id: int, qty: int, kind: str, user_id: int, company_id: int):
    product = db.query(Product).filter_by(id=product_id, company_id=company_id).first()

    if not product:
        return False, "Produto não encontrado"

    if product.stock < qty:
        return False, f"Estoque insuficiente ({product.stock})"

    product.stock -= qty

    sale = Sale(
        product_id=product.id,
        quantity=qty,
        price=product.price_retail,
        kind=kind,
        user_id=user_id,
        company_id=company_id,
        date=datetime.now()
    )
    db.add(sale)
    db.commit()
    return True, "Venda realizada"

# =========================
# 💰 FINANCEIRO
# =========================

def add_expense(db: Session, company_id: int, desc, amount, category, date):
    exp = Expense(
        description=desc,
        amount=amount,
        category=category,
        company_id=company_id,
        date=date
    )
    db.add(exp)
    db.commit()

def get_financial_by_range(db: Session, company_id: int, start_date, end_date):
    sales_q = db.query(
        Sale.date,
        Sale.quantity,
        Sale.price,
        Product.name.label("product_name")
    ).join(Product).filter(
        Sale.company_id == company_id,
        Sale.date >= start_date,
        Sale.date <= end_date
    ).statement

    expense_q = db.query(
        Expense.date,
        Expense.category,
        Expense.description,
        Expense.amount
    ).filter(
        Expense.company_id == company_id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).statement

    df_sales = pd.read_sql(sales_q, db.bind)
    df_exp = pd.read_sql(expense_q, db.bind)
    return df_sales, df_exp


