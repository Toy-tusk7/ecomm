from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, abort
from flask_login import current_user, login_required
from app.models import db, Product, Category, CartItem, Order, OrderItem

main_bp = Blueprint('main', __name__)

@main_bp.app_context_processor
def inject_cart_count():
    count = 0
    if current_user.is_authenticated:
        count = sum(item.quantity for item in current_user.cart_items.all())
    else:
        cart = session.get('cart', {})
        count = sum(cart.values())
    return dict(cart_count=count)

@main_bp.route('/')
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
            
    if query:
        products_query = products_query.filter(
            (Product.name.ilike(f'%{query}%')) | 
            (Product.description.ilike(f'%{query}%'))
        )
        
    products = products_query.all()
    return render_template('main/index.html', products=products, categories=categories, selected_category=selected_category, query=query)

@main_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()
    # Recommended products (same category, excluding current product)
    recommended = Product.query.filter(Product.category_id == product.category_id, Product.id != product.id).limit(4).all()
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
            db.session.add(item)
        db.session.commit()
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
            db.session.commit()
    else:
        cart = session.get('cart', {})
        str_id = str(product_id)
        if str_id in cart:
            cart[str_id] = qty
            session['cart'] = cart
            
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return updated JSON totals
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
            db.session.delete(item)
            db.session.commit()
    else:
        cart = session.get('cart', {})
        str_id = str(product_id)
        if str_id in cart:
            cart.pop(str_id)
            session['cart'] = cart
            
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Calculate new total
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
            payment_method=payment
        )
        db.session.add(new_order)
        db.session.commit() # Get order ID
        
        # Move items to order history and decrement product stocks
        for item in order_items:
            o_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(o_item)
            # Decrement stock
            item.product.stock -= item.quantity
            
            # Delete cart item
            db.session.delete(item)
            
        db.session.commit()
        flash('Thank you! Your order has been placed successfully.', 'success')
        return redirect(url_for('main.orders'))
        
    return render_template('main/checkout.html', cart_items=cart_items, total=total)

@main_bp.route('/orders')
@login_required
def orders():
    user_orders = current_user.orders.order_by(Order.created_at.desc()).all()
    return render_template('main/orders.html', orders=user_orders)
