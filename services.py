import hashlib
from sqlalchemy.orm import Session
from datetime import datetime
from models import User, Company, Product, Sale, Expense

# ------------------ SEGURANÇA ------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and user.password_hash == hash_password(password):
        return user
    return None

def create_initial_data(db: Session):
    company = db.query(Company).filter(Company.id == 1).first()
    if not company:
        company = Company(
            id=1,
            name="Empresa Inicial",
            license_key="LIC-001",
            is_active=True
        )
        db.add(company)
        db.commit()

    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            company_id=1
        )
        db.add(admin)
        db.commit()

# ------------------ USUÁRIOS ------------------

def list_users(db: Session, company_id: int):
    return db.query(User).filter(User.company_id == company_id).all()

def create_user(db: Session, company_id: int, username: str, password: str, role: str):
    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        company_id=company_id
    )
    db.add(user)
    db.commit()

def delete_user(db: Session, user_id: int, company_id: int):
    user = db.query(User).filter(
        User.id == user_id,
        User.company_id == company_id
    ).first()
    if user:
        db.delete(user)
        db.commit()

def change_password(db: Session, user_id: int, new_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.password_hash = hash_password(new_password)
        db.commit()

# ------------------ PRODUTOS / VENDAS ------------------

def get_products(db: Session, company_id: int):
    return db.query(Product).filter(Product.company_id == company_id).all()

def register_product(db: Session, company_id: int, name, price_retail, price_wholesale, stock_min, sku):
    p = Product(
        name=name,
        price_retail=price_retail,
        price_wholesale=price_wholesale,
        stock=0,
        stock_min=stock_min,
        sku=sku,
        company_id=company_id
    )
    db.add(p)
    db.commit()

def process_sale(db: Session, product_id, qty, kind, user_id, company_id):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == company_id
    ).first()
    if not product or product.stock < qty:
        return False
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
    return True


