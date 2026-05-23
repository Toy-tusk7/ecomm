import os
from flask import Flask
from flask_login import LoginManager
from app.models import db, User, Category, Product
from app.config import Config

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extension objects
    db.init_app(app)
    login_manager.init_app(app)
    
    # Ensure static directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register Blueprints
    from app.views.auth import auth_bp
    from app.views.main import main_bp
    from app.views.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    
    # Database seeding context
    with app.app_context():
        db.create_all()
        seed_database()
        
    return app

def seed_database():
    try:
        # Seed default Admin User if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_user = User(
                username='admin',
                email='admin@ecomm.com',
                is_admin=True
            )
            admin_user.set_password('adminpassword')
            db.session.add(admin_user)
            db.session.commit() # Commit immediately to release table locks
            
        # Seed default Standard Customer User if not exists
        customer = User.query.filter_by(username='user').first()
        if not customer:
            customer_user = User(
                username='user',
                email='user@ecomm.com',
                is_admin=False
            )
            customer_user.set_password('userpassword')
            db.session.add(customer_user)
            db.session.commit() # Commit immediately to release table locks
            
        # Seed default Categories if not exists
        categories_data = [
            {'name': 'Mechanical Keyboards', 'slug': 'keyboards'},
            {'name': 'Audio Gear', 'slug': 'audio'},
            {'name': 'Gaming Mice', 'slug': 'mice'},
            {'name': 'Ambient Lighting', 'slug': 'lighting'}
        ]
        
        for cat_info in categories_data:
            existing_cat = Category.query.filter_by(slug=cat_info['slug']).first()
            if not existing_cat:
                cat = Category(name=cat_info['name'], slug=cat_info['slug'])
                db.session.add(cat)
                
        db.session.commit()
        
        # Seed default Products if not exists
        keyboards_cat = Category.query.filter_by(slug='keyboards').first()
        audio_cat = Category.query.filter_by(slug='audio').first()
        mice_cat = Category.query.filter_by(slug='mice').first()
        lighting_cat = Category.query.filter_by(slug='lighting').first()
        
        products_data = [
            {
                'name': 'Spectra-80 Mechanical Keyboard',
                'description': 'A premium 80% layout mechanical keyboard with custom tuned linear switches, hot-swappable sockets, and addressable obsidian-glow RGB backlighting inside a frosted polycarbonate casing.',
                'price': 189.99,
                'stock': 15,
                'image_url': '/static/uploads/keyboard.jpg',
                'category_id': keyboards_cat.id
            },
            {
                'name': 'AeroFlow Cyberpunk ANC Headphones',
                'description': 'Studio-grade acoustic audio featuring active hybrid noise cancellation, 40-hour ultra battery life, custom equalizer profiles, and futuristic translucent glowing design accent rings.',
                'price': 249.99,
                'stock': 8,
                'image_url': '/static/uploads/headphones.jpg',
                'category_id': audio_cat.id
            },
            {
                'name': 'NovaPrecision Wireless Pro Mouse',
                'description': 'Ultra-lightweight 58-gram gaming mouse with an optical 26,000 DPI sensor, magnetic switch triggers, and lag-free dual wireless connectivity modes.',
                'price': 89.99,
                'stock': 25,
                'image_url': '/static/uploads/mouse.jpg',
                'category_id': mice_cat.id
            },
            {
                'name': 'Aurora Smart Ambient Lamp',
                'description': 'A glassmorphic intelligent light sphere offering multi-zone color blending, music synchronization, smart home ecosystem controls, and dynamic sunset/sunrise schedules.',
                'price': 59.99,
                'stock': 30,
                'image_url': '/static/uploads/lamp.jpg',
                'category_id': lighting_cat.id
            }
        ]
        
        for prod_info in products_data:
            existing_prod = Product.query.filter_by(name=prod_info['name']).first()
            if not existing_prod:
                prod = Product(
                    name=prod_info['name'],
                    description=prod_info['description'],
                    price=prod_info['price'],
                    stock=prod_info['stock'],
                    image_url=prod_info['image_url'],
                    category_id=prod_info['category_id']
                )
                db.session.add(prod)
                
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Database seeding bypassed or already complete: {e}")
