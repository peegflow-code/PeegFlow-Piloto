from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash
from models import User, Product, Sale, Expense
import pandas as pd
from datetime import datetime

# ---------- AUTH ----------

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and check_password_hash(user.password_hash, password):
        return user
    return None


def require_admin(user):
    if user.role != "admin":
        raise PermissionError("Acesso restrito a administradores")


# ---------- PRODUTOS ----------

def get_products(db, company_id):
    return db.query(Product).filter(Product.company_id == company_id).all()


def register_product(db, company_id, name, price_sale, price_cost, stock_min, sku):
    prod = Product(
        company_id=company_id,
        name=name,
        sku=sku,
        price_retail=price_sale,
        price_wholesale=price_cost,
        stock=0,
        stock_min=stock_min
    )
    db.add(prod)
    db.commit()


def restock_product(db, company_id, product_id, qty, cost):
    prod = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == company_id
    ).first()

    prod.stock += qty

    expense = Expense(
        company_id=company_id,
        description=f"Reposição estoque: {prod.name}",
        category="Estoque",
        amount=qty * cost,
        date=datetime.utcnow()
    )

    db.add(expense)
    db.commit()


# ---------- FINANCEIRO ----------

def add_expense(db, company_id, desc, val, cat, date):
    exp = Expense(
        company_id=company_id,
        description=desc,
        category=cat,
        amount=val,
        date=date
    )
    db.add(exp)
    db.commit()


def get_financial_by_range(db, company_id, start, end):
    sales = db.query(Sale).filter(
        Sale.company_id == company_id,
        Sale.date >= start,
        Sale.date <= end
    ).all()

    expenses = db.query(Expense).filter(
        Expense.company_id == company_id,
        Expense.date >= start,
        Expense.date <= end
    ).all()

    df_sales = pd.DataFrame([{
        "date": s.date,
        "product_id": s.product_id,
        "quantity": s.quantity,
        "price": s.price,
        "user_id": s.user_id
    } for s in sales])

    df_exp = pd.DataFrame([{
        "date": e.date,
        "description": e.description,
        "category": e.category,
        "amount": e.amount
    } for e in expenses])

    return df_sales, df_exp

