from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, abort
from flask_login import current_user, login_required
from app.firebase_db import User, Product, Category, CartItem, Order, OrderItem

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def elrs_landing():
    """Apple-style scroll animation landing page for the ELRS Pico LoRa Controller."""
    product = Product.query.filter_by(name='ELRS Pico LoRa Controller').first()
    return render_template('main/elrs_landing.html', product=product)

@main_bp.route('/elrs')
def elrs_redirect():
    return redirect(url_for('main.elrs_landing'))

@main_bp.route('/about')
def about():
    """About page containing design-led studio info from the old site."""
    return render_template('main/about.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact Us inquiry form page."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        
        # Save inquiry in mock database if needed, otherwise just flash success
        flash('Inquiry received. Thanks! Your message is ready for review.', 'success')
        return redirect(url_for('main.contact'))
        
    return render_template('main/contact.html')

@main_bp.route('/privacy')
def privacy():
    """Privacy Policy page."""
    return render_template('main/privacy.html')

@main_bp.route('/terms')
def terms():
    """Terms of Service page."""
    return render_template('main/terms.html')

@main_bp.route('/cookies')
def cookies():
    """Cookie Policy page."""
    return render_template('main/cookies.html')

@main_bp.app_context_processor
def inject_cart_count():
    count = 0
    if current_user.is_authenticated:
        count = sum(item.quantity for item in current_user.cart_items.all())
    else:
        cart = session.get('cart', {})
        count = sum(cart.values())
    return dict(cart_count=count)

@main_bp.route('/products')
def index():
    query = request.args.get('q', '').strip()
    category_slug = request.args.get('category', '').strip()
    
    categories = Category.query.all()
    products_query = Product.query
    
    selected_category = None
    if category_slug:
        selected_category = Category.query.filter_by(slug=category_slug).first()
        if selected_category:
            products_query = products_query.filter_by(category_id=selected_category.id)
            
    products = products_query.all()
    if query:
        q = query.lower()
        products = [p for p in products if q in p.name.lower() or (p.description and q in p.description.lower())]
        
    return render_template('main/index.html', products=products, categories=categories, selected_category=selected_category, query=query)

@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()
    
    # Recommended products (same category, excluding current product)
    recommended_query = Product.query.filter_by(category_id=product.category_id)
    recommended = [p for p in recommended_query.all() if p.id != product.id][:4]
    
    return render_template('main/product.html', product=product, categories=categories, recommended=recommended)

@main_bp.route('/cart')
def cart():
    cart_data = []
    total = 0.0
    
    if current_user.is_authenticated:
        db_items = current_user.cart_items.all()
        for item in db_items:
            subtotal = item.product.price * item.quantity
            total += subtotal
            cart_data.append({
                'product': item.product,
                'quantity': item.quantity,
                'subtotal': subtotal
            })
    else:
        session_cart = session.get('cart', {})
        for product_id, quantity in list(session_cart.items()):
            product = Product.query.get(int(product_id))
            if product:
                subtotal = product.price * quantity
                total += subtotal
                cart_data.append({
                    'product': product,
                    'quantity': quantity,
                    'subtotal': subtotal
                })
            else:
                # Remove invalid product from cart
                session_cart.pop(str(product_id), None)
        session['cart'] = session_cart
        
    return render_template('main/cart.html', cart_items=cart_data, total=total)

@main_bp.route('/cart/add/<int:product_id>', methods=['POST'])
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        qty = int(request.form.get('quantity', 1))
    except ValueError:
        qty = 1
        
    if qty < 1:
        qty = 1
        
    if product.stock < qty:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'Not enough stock. Only {product.stock} available.'}), 400
        flash(f'Only {product.stock} items available in stock.', 'error')
        return redirect(url_for('main.product_detail', product_id=product_id))
        
    if current_user.is_authenticated:
        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        if item:
            item.quantity += qty
        else:
            item = CartItem(user_id=current_user.id, product_id=product.id, quantity=qty)
        item.save()
    else:
        cart = session.get('cart', {})
        str_id = str(product_id)
        cart[str_id] = cart.get(str_id, 0) + qty
        session['cart'] = cart
        
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        count = sum(item.quantity for item in current_user.cart_items.all()) if current_user.is_authenticated else sum(session.get('cart', {}).values())
        return jsonify({'success': True, 'message': f'{product.name} added to cart.', 'cart_count': count})
        
    flash(f'{product.name} added to cart.', 'success')
    return redirect(url_for('main.cart'))

@main_bp.route('/cart/update/<int:product_id>', methods=['POST'])
def cart_update(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        qty = int(request.form.get('quantity'))
    except (ValueError, TypeError):
        qty = 1
        
    if qty < 1:
        qty = 1
        
    if product.stock < qty:
        qty = product.stock
        flash(f'Quantity adjusted to maximum available stock ({product.stock}).', 'warning')
        
    if current_user.is_authenticated:
        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        if item:
            item.quantity = qty
            item.save()
    else:
        cart = session.get('cart', {})
        str_id = str(product_id)
        if str_id in cart:
            cart[str_id] = qty
            session['cart'] = cart
            
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        subtotal = product.price * qty
        total = 0.0
        if current_user.is_authenticated:
            db_items = current_user.cart_items.all()
            total = sum(i.product.price * i.quantity for i in db_items)
            count = sum(i.quantity for i in db_items)
        else:
            session_cart = session.get('cart', {})
            total = sum(Product.query.get(int(pid)).price * q for pid, q in session_cart.items() if Product.query.get(int(pid)))
            count = sum(session_cart.values())
        return jsonify({
            'success': True, 
            'subtotal': f'${subtotal:.2f}', 
            'total': f'${total:.2f}',
            'cart_count': count
        })
        
    return redirect(url_for('main.cart'))

@main_bp.route('/cart/remove/<int:product_id>', methods=['POST', 'GET'])
def cart_remove(product_id):
    product = Product.query.get_or_404(product_id)
    
    if current_user.is_authenticated:
        item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        if item:
            item.delete()
    else:
        cart = session.get('cart', {})
        str_id = str(product_id)
        if str_id in cart:
            cart.pop(str_id)
            session['cart'] = cart
            
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        total = 0.0
        if current_user.is_authenticated:
            db_items = current_user.cart_items.all()
            total = sum(i.product.price * i.quantity for i in db_items)
            count = sum(i.quantity for i in db_items)
        else:
            session_cart = session.get('cart', {})
            total = sum(Product.query.get(int(pid)).price * q for pid, q in session_cart.items() if Product.query.get(int(pid)))
            count = sum(session_cart.values())
        return jsonify({
            'success': True,
            'message': f'{product.name} removed from cart.',
            'total': f'${total:.2f}',
            'cart_count': count
        })
        
    flash(f'{product.name} removed from cart.', 'success')
    return redirect(url_for('main.cart'))

@main_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = current_user.cart_items.all()
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('main.cart'))
        
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    if request.method == 'POST':
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        zip_code = request.form.get('zip_code', '').strip()
        payment = request.form.get('payment_method', 'Credit Card')
        
        if not address or not city or not zip_code:
            flash('Please complete all shipping address fields.', 'error')
            return render_template('main/checkout.html', cart_items=cart_items, total=total)
            
        shipping_full = f"{address}, {city}, {zip_code}"
        
        # Verify stock and build order items
        order_items = []
        for item in cart_items:
            if item.product.stock < item.quantity:
                flash(f'Sorry, stock limit exceeded for {item.product.name}. Limit is {item.product.stock}. Please adjust cart.', 'error')
                return redirect(url_for('main.cart'))
            order_items.append(item)
            
        # Create Order
        new_order = Order(
            user_id=current_user.id,
            status='Paid',  # Mock successful payment
            total_price=total,
            shipping_address=shipping_full,
            payment_method=payment,
            created_at=datetime.utcnow()
        )
        new_order.save()
        
        # Move items to order history and decrement product stocks
        for item in order_items:
            o_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            o_item.save()
            
            # Decrement stock
            prod = item.product
            if prod:
                prod.stock -= item.quantity
                prod.save()
                
            # Delete cart item
            item.delete()
            
        flash('Thank you! Your order has been placed successfully.', 'success')
        return redirect(url_for('main.orders'))
        
    return render_template('main/checkout.html', cart_items=cart_items, total=total)

@main_bp.route('/orders')
@login_required
def orders():
    user_orders = current_user.orders.order_by(Order.created_at.desc()).all()
    return render_template('main/orders.html', orders=user_orders)
