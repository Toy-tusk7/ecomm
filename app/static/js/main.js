// Page Loader Logo Transition
window.addEventListener('load', () => {
    const loaderOverlay = document.getElementById('loader-overlay');
    const loaderLogo = document.getElementById('loader-logo-container');
    const navbarBrand = document.getElementById('navbar-brand');
    
    // Check if the loader has already played in this browser session
    if (sessionStorage.getItem('tedh_loader_played') === 'true') {
        if (loaderOverlay) loaderOverlay.style.display = 'none';
        if (navbarBrand) navbarBrand.classList.add('show-brand');
        return;
    }
    
    if (loaderOverlay && loaderLogo && navbarBrand) {
        // Trigger the transition after a brief visual pause
        setTimeout(() => {
            const startRect = loaderLogo.getBoundingClientRect();
            const destRect = navbarBrand.getBoundingClientRect();
            
            // Calculate center offsets
            const startX = startRect.left + startRect.width / 2;
            const startY = startRect.top + startRect.height / 2;
            const destX = destRect.left + destRect.width / 2;
            const destY = destRect.top + destRect.height / 2;
            
            const dx = destX - startX;
            const dy = destY - startY;
            const scale = destRect.width / startRect.width;
            
            // Start the translation & shrink
            loaderLogo.style.transform = `translate(${dx}px, ${dy}px) scale(${scale})`;
            
            // Record that the loader has run for this session
            sessionStorage.setItem('tedh_loader_played', 'true');
            
            // Fade out the overlay background and show the navbar brand
            setTimeout(() => {
                loaderOverlay.classList.add('fade-out');
                navbarBrand.classList.add('show-brand');
            }, 450);
            
            // Clean up loader overlay
            setTimeout(() => {
                loaderOverlay.style.display = 'none';
            }, 1200);
        }, 300);
    } else {
        if (loaderOverlay) loaderOverlay.style.display = 'none';
        if (navbarBrand) navbarBrand.classList.add('show-brand');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    // 1. Toast Notification Setup
    ensureToastContainer();
    
    // Convert Flask flashed messages (if any exist in DOM) to toast notifications
    const flashedMessages = document.querySelectorAll('.flash-data');
    flashedMessages.forEach(msg => {
        const text = msg.getAttribute('data-message');
        const category = msg.getAttribute('data-category') || 'info';
        showToast(text, category);
    });

    // 2. Parallax Hover Effect for Product Cards
    const cards = document.querySelectorAll('.product-card');
    cards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--x', `${x}px`);
            card.style.setProperty('--y', `${y}px`);
        });
    });

    // 3. Asynchronous Add to Cart
    const addForms = document.querySelectorAll('.add-to-cart-form');
    addForms.forEach(form => {
        form.addEventListener('submit', async e => {
            e.preventDefault();
            const actionUrl = form.getAttribute('action');
            const formData = new FormData(form);
            
            try {
                const response = await fetch(actionUrl, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();
                
                if (response.ok && data.success) {
                    showToast(data.message, 'success');
                    updateCartBadge(data.cart_count);
                } else {
                    showToast(data.message || 'Failed to add item to cart.', 'error');
                }
            } catch (error) {
                console.error('Error adding to cart:', error);
                showToast('Failed to add item to cart. Please try again.', 'error');
            }
        });
    });

    // 4. Cart Page Quantity and Deletion Ajax
    setupCartActions();
});

// Helper: Ensure toast container exists
function ensureToastContainer() {
    if (!document.querySelector('.toast-container')) {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
}

// Function: Display dynamic toast alerts
function showToast(message, type = 'info') {
    ensureToastContainer();
    const container = document.querySelector('.toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    // Choose icons based on toast category
    let icon = '💡';
    if (type === 'success') icon = '⚡';
    if (type === 'error') icon = '❌';
    if (type === 'warning') icon = '⚠️';
    
    toast.innerHTML = `
        <div class="toast-content">
            <span>${icon}</span>
            <span>${message}</span>
        </div>
        <button class="toast-close">&times;</button>
    `;
    
    container.appendChild(toast);
    
    // Close button click
    toast.querySelector('.toast-close').addEventListener('click', () => {
        removeToast(toast);
    });
    
    // Auto remove toast
    setTimeout(() => {
        removeToast(toast);
    }, 4000);
}

function removeToast(toast) {
    toast.style.transform = 'translateX(120%)';
    toast.style.opacity = '0';
    setTimeout(() => {
        toast.remove();
    }, 300);
}

// Function: Update Cart Header Badge
function updateCartBadge(count) {
    const badgeContainer = document.querySelector('.nav-actions');
    let badge = document.querySelector('.cart-badge');
    
    if (count > 0) {
        if (!badge) {
            // Find cart button and inject badge
            const cartBtn = document.querySelector('.cart-nav-btn');
            if (cartBtn) {
                badge = document.createElement('span');
                badge.className = 'cart-badge';
                cartBtn.appendChild(badge);
            }
        }
        if (badge) {
            badge.textContent = count;
            // Add bounce animation
            badge.style.transform = 'scale(1.3)';
            setTimeout(() => {
                badge.style.transform = '';
            }, 200);
        }
    } else {
        if (badge) badge.remove();
    }
}

// Cart View Interactions (Update & Delete)
function setupCartActions() {
    const cartTable = document.querySelector('.cart-grid');
    if (!cartTable) return;
    
    // Quantity Adjusters
    const qtySelectors = document.querySelectorAll('.qty-selector');
    qtySelectors.forEach(selector => {
        const input = selector.querySelector('.qty-input');
        const minusBtn = selector.querySelector('.minus');
        const plusBtn = selector.querySelector('.plus');
        const productId = input.getAttribute('data-product-id');
        
        const updateQty = async (newVal) => {
            input.value = newVal;
            
            const formData = new FormData();
            formData.append('quantity', newVal);
            
            try {
                const response = await fetch(`/cart/update/${productId}`, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();
                if (response.ok && data.success) {
                    // Update subtotal
                    const itemRow = selector.closest('.cart-item');
                    const subtotalEl = itemRow.querySelector('.cart-item-subtotal');
                    if (subtotalEl) {
                        subtotalEl.textContent = data.subtotal;
                    }
                    
                    // Update cart total
                    const totalEls = document.querySelectorAll('.cart-total-value');
                    totalEls.forEach(el => el.textContent = data.total);
                    
                    // Update badge
                    updateCartBadge(data.cart_count);
                }
            } catch (err) {
                console.error('Error updating quantity:', err);
                showToast('Failed to update quantity.', 'error');
            }
        };
        
        minusBtn.addEventListener('click', () => {
            let val = parseInt(input.value) || 1;
            if (val > 1) {
                updateQty(val - 1);
            }
        });
        
        plusBtn.addEventListener('click', () => {
            let val = parseInt(input.value) || 1;
            updateQty(val + 1);
        });
        
        input.addEventListener('change', () => {
            let val = parseInt(input.value) || 1;
            if (val < 1) val = 1;
            updateQty(val);
        });
    });

    // Remove buttons AJAX
    const removeBtns = document.querySelectorAll('.cart-item-remove-form');
    removeBtns.forEach(form => {
        form.addEventListener('submit', async e => {
            e.preventDefault();
            const actionUrl = form.getAttribute('action');
            const itemRow = form.closest('.cart-item');
            
            try {
                const response = await fetch(actionUrl, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                const data = await response.json();
                
                if (response.ok && data.success) {
                    // Animate item away
                    itemRow.style.transform = 'scale(0.9)';
                    itemRow.style.opacity = '0';
                    
                    setTimeout(() => {
                        itemRow.remove();
                        // Update cart total
                        const totalEls = document.querySelectorAll('.cart-total-value');
                        totalEls.forEach(el => el.textContent = data.total);
                        // Update badge
                        updateCartBadge(data.cart_count);
                        
                        // Check if cart is now empty
                        const remainingItems = document.querySelectorAll('.cart-item');
                        if (remainingItems.length === 0) {
                            // Reload to show empty state template
                            window.location.reload();
                        }
                    }, 300);
                    
                    showToast(data.message, 'success');
                } else {
                    showToast(data.message || 'Failed to remove item.', 'error');
                }
            } catch (err) {
                console.error('Error removing item:', err);
                showToast('Failed to remove item.', 'error');
            }
        });
    });
}
