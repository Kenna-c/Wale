from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal

from .models import Cart, CartItem, Order, OrderItem, MpesaPayment
from shop.models import Product


# ── Cart ────────────────────────────────────────────────
@login_required
def cart(request):
    cart_obj, _ = Cart.objects.get_or_create(user=request.user)
    items       = cart_obj.items.select_related('product__category', 'product__brand')
    return render(request, 'payments/cart.html', {
        'cart': cart_obj,
        'items': items,
    })


@login_required
@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    qty     = int(request.POST.get('quantity', 1))
    cart_obj, _ = Cart.objects.get_or_create(user=request.user)

    item, created = CartItem.objects.get_or_create(cart=cart_obj, product=product)
    if not created:
        item.quantity = min(item.quantity + qty, product.stock)
    else:
        item.quantity = min(qty, product.stock)
    item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'count': cart_obj.item_count, 'added': True})

    messages.success(request, f'"{product.name}" added to cart!')
    return redirect(request.META.get('HTTP_REFERER', 'payments:cart'))


@login_required
@require_POST
def update_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    action = request.POST.get('action')
    if action == 'increase':
        item.quantity = min(item.quantity + 1, item.product.stock)
        item.save()
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()
    elif action == 'remove':
        item.delete()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_obj = Cart.objects.get(user=request.user)
        return JsonResponse({'count': cart_obj.item_count, 'total': str(cart_obj.total)})

    return redirect('payments:cart')


# ── Checkout ────────────────────────────────────────────
@login_required
def checkout(request):
    cart_obj = get_object_or_404(Cart, user=request.user)
    items    = cart_obj.items.select_related('product')
    if not items.exists():
        messages.warning(request, 'Your cart is empty.')
        return redirect('payments:cart')

    SHIPPING_FEE = Decimal('300.00')
    subtotal = cart_obj.total
    total    = subtotal + SHIPPING_FEE

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone     = request.POST.get('phone', '').strip()
        email     = request.POST.get('email', '').strip()
        address   = request.POST.get('address', '').strip()
        city      = request.POST.get('city', '').strip()
        county    = request.POST.get('county', '').strip()
        notes     = request.POST.get('notes', '').strip()

        if not all([full_name, phone, email, address, city, county]):
            messages.error(request, 'Please fill all required fields.')
        else:
            order = Order.objects.create(
                user=request.user,
                full_name=full_name,
                phone=phone,
                email=email,
                address=address,
                city=city,
                county=county,
                notes=notes,
                subtotal=subtotal,
                shipping_fee=SHIPPING_FEE,
                total=total,
            )
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.product.price,
                )
            items.delete()  # clear cart
            return redirect('payments:mpesa_payment', pk=order.pk)

    return render(request, 'payments/checkout.html', {
        'cart': cart_obj,
        'items': items,
        'subtotal': subtotal,
        'shipping_fee': SHIPPING_FEE,
        'total': total,
        'user': request.user,
    })


# ── M-Pesa Payment ──────────────────────────────────────
@login_required
def mpesa_payment(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)

    if hasattr(order, 'mpesa_payment') and order.mpesa_payment.status != 'rejected':
        return redirect('payments:payment_confirmation', pk=order.pk)

    if request.method == 'POST':
        mpesa_phone      = request.POST.get('mpesa_phone', '').strip()
        transaction_code = request.POST.get('transaction_code', '').strip().upper()
        amount_paid      = request.POST.get('amount_paid', '0').strip()
        screenshot       = request.FILES.get('payment_screenshot')

        errors = {}
        if not mpesa_phone:
            errors['mpesa_phone'] = 'Phone number is required.'
        if not transaction_code or len(transaction_code) < 8:
            errors['transaction_code'] = 'Please enter a valid M-Pesa confirmation code.'
        try:
            amount_paid = Decimal(amount_paid)
            if amount_paid <= 0:
                errors['amount_paid'] = 'Enter a valid amount.'
        except Exception:
            errors['amount_paid'] = 'Enter a valid amount.'

        if not errors:
            mp = MpesaPayment(
                order=order,
                mpesa_phone=mpesa_phone,
                transaction_code=transaction_code,
                amount_paid=amount_paid,
            )
            if screenshot:
                mp.payment_screenshot = screenshot
            mp.save()
            order.status = 'confirming'
            order.save()
            return redirect('payments:payment_confirmation', pk=order.pk)

        return render(request, 'payments/mpesa_payment.html', {
            'order': order,
            'errors': errors,
            'form_data': request.POST,
        })

    return render(request, 'payments/mpesa_payment.html', {'order': order})


# ── Payment Confirmation ────────────────────────────────
@login_required
def payment_confirmation(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'payments/confirmation.html', {'order': order})


# ── Order Detail ─────────────────────────────────────────
@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'payments/order_detail.html', {'order': order})