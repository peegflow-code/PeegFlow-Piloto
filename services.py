from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import bcrypt
import pandas as pd

from models import User, Product, Sale, Expense, Company

def create_company_with_admin(
    db: Session,
    company_name: str,
    username: str,
    password: str
):
    # Empresa
    company = Company(name=company_name)
    db.add(company)
    db.commit()
    db.refresh(company)

    # Hash da senha
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    admin = User(
        username=username,
        password_hash=password_hash,
        role="admin",
        company_id=company.id
    )
    db.add(admin)
    db.commit()

    return company

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None

    if bcrypt.checkpw(
        password.encode("utf-8"),
        user.password_hash.encode("utf-8")
    ):
        return user

    return None


def get_products(db: Session, company_id: int):
    return (
        db.query(Product)
        .filter(Product.company_id == company_id)
        .order_by(Product.name)
        .all()
    )


def register_product(
    db: Session,
    company_id: int,
    name: str,
    price_retail: float,
    price_wholesale: float,
    stock_min: int,
    sku: str
):
    product = Product(
        name=name,
        sku=sku,
        price_retail=price_retail,
        price_wholesale=price_wholesale,
        stock=0,
        stock_min=stock_min,
        company_id=company_id
    )
    db.add(product)
    db.commit()
    return product

def restock_product(
    db: Session,
    company_id: int,
    product_id: int,
    quantity: int,
    unit_cost: float
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.company_id == company_id
        )
        .first()
    )

    if not product:
        raise Exception("Produto não encontrado")

    # Atualiza estoque
    product.stock += quantity

    # Lança despesa automática
    expense = Expense(
        description=f"Reposição de estoque: {product.name}",
        amount=quantity * unit_cost,
        category="Estoque",
        company_id=company_id,
        date=datetime.utcnow()
    )

    db.add(expense)
    db.commit()

def process_sale(
    db: Session,
    company_id: int,
    product_id: int,
    quantity: int,
    kind: str,
    user_id: int
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.company_id == company_id
        )
        .first()
    )

    if not product:
        raise Exception("Produto não encontrado")

    if product.stock < quantity:
        raise Exception("Estoque insuficiente")

    price = (
        product.price_wholesale
        if kind == "atacado"
        else product.price_retail
    )

    sale = Sale(
        product_id=product.id,
        quantity=quantity,
        price=price,
        kind=kind,
        user_id=user_id,
        company_id=company_id,
        date=datetime.utcnow()
    )

    product.stock -= quantity

    db.add(sale)
    db.commit()

def add_expense(
    db: Session,
    company_id: int,
    description: str,
    amount: float,
    category: str,
    date: datetime
):
    expense = Expense(
        description=description,
        amount=amount,
        category=category,
        company_id=company_id,
        date=date
    )
    db.add(expense)
    db.commit()

def get_financial_by_range(
    db: Session,
    company_id: int,
    start_date: datetime,
    end_date: datetime
):
    sales = (
        db.query(
            Sale.date,
            Sale.quantity,
            Sale.price,
            Product.name.label("product_name")
        )
        .join(Product, Product.id == Sale.product_id)
        .filter(
            Sale.company_id == company_id,
            Sale.date.between(start_date, end_date)
        )
        .all()
    )

    expenses = (
        db.query(
            Expense.date,
            Expense.category,
            Expense.description,
            Expense.amount
        )
        .filter(
            Expense.company_id == company_id,
            Expense.date.between(start_date, end_date)
        )
        .all()
    )

    df_sales = pd.DataFrame(sales)
    df_expenses = pd.DataFrame(expenses)

    return df_sales, df_expenses
