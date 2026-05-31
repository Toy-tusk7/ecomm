import os
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app.firebase_db import Product, Category, Order, User

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Check for allowed image extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    products = Product.query.all()
    categories = Category.query.all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    users_count = User.query.count()
    
    total_sales = sum(o.total_price for o in orders if o.status not in ('Cancelled', 'Pending'))
    
    return render_template(
        'admin/dashboard.html', 
        products=products, 
        categories=categories, 
        orders=orders, 
        users_count=users_count,
        total_sales=total_sales
    )

@admin_bp.route('/product/new', methods=['GET', 'POST'])
@admin_required
def product_new():
    categories = Category.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        try:
            price = float(request.form.get('price', 0))
            stock = int(request.form.get('stock', 0))
            category_id = int(request.form.get('category_id'))
        except (ValueError, TypeError):
            flash('Invalid numeric inputs. Check price, stock, and category fields.', 'error')
            return render_template('admin/product_form.html', categories=categories, product=None)
            
        if not name or not category_id:
            flash('Product name and category are required.', 'error')
            return render_template('admin/product_form.html', categories=categories, product=None)
            
        # File Upload Handler
        image_url = '/static/uploads/default.png'
        file = request.files.get('image')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                image_url = f'/static/uploads/{filename}'
            else:
                flash('Invalid image format. Allowed formats: png, jpg, jpeg, gif, webp.', 'error')
                return render_template('admin/product_form.html', categories=categories, product=None)
                
        # Create product
        new_prod = Product(
            name=name,
            description=description,
            price=price,
            stock=stock,
            image_url=image_url,
            category_id=category_id
        )
        
        try:
            new_prod.save()
            flash(f'Product "{name}" added successfully.', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            flash('Error creating product. Please try again.', 'error')
            
    return render_template('admin/product_form.html', categories=categories, product=None)

@admin_bp.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        try:
            price = float(request.form.get('price', 0))
            stock = int(request.form.get('stock', 0))
            category_id = int(request.form.get('category_id'))
        except (ValueError, TypeError):
            flash('Invalid numeric inputs. Check price, stock, and category fields.', 'error')
            return render_template('admin/product_form.html', categories=categories, product=product)
            
        if not name or not category_id:
            flash('Product name and category are required.', 'error')
            return render_template('admin/product_form.html', categories=categories, product=product)
            
        # File Upload Handler
        file = request.files.get('image')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                product.image_url = f'/static/uploads/{filename}'
            else:
                flash('Invalid image format. Allowed formats: png, jpg, jpeg, gif, webp.', 'error')
                return render_template('admin/product_form.html', categories=categories, product=product)
                
        # Update details
        product.name = name
        product.description = description
        product.price = price
        product.stock = stock
        product.category_id = category_id
        
        try:
            product.save()
            flash(f'Product "{name}" updated successfully.', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            flash('Error updating product. Please try again.', 'error')
            
    return render_template('admin/product_form.html', categories=categories, product=product)

@admin_bp.route('/product/delete/<int:product_id>', methods=['POST'])
@admin_required
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    name = product.name
    
    try:
        product.delete()
        flash(f'Product "{name}" deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting product "{name}". It might have order histories.', 'error')
        
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/orders')
@admin_required
def orders():
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=all_orders)

@admin_bp.route('/order/status/<int:order_id>', methods=['POST'])
@admin_required
def order_status(order_id):
    order = Order.query.get_or_404(order_id)
    status = request.form.get('status')
    
    if status in ('Pending', 'Paid', 'Shipped', 'Completed', 'Cancelled'):
        order.status = status
        order.save()
        flash(f'Order #{order.id} status updated to {status}.', 'success')
    else:
        flash('Invalid status option selected.', 'error')
        
    return redirect(url_for('admin.orders'))
