from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import Profile
from payments.models import Order

User = get_user_model()


# ── Register ────────────────────────────────────────────
def register(request):
    if request.user.is_authenticated:
        return redirect('shop:home')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip().lower()
        username   = request.POST.get('username', '').strip()
        phone      = request.POST.get('phone', '').strip()
        password1  = request.POST.get('password1', '')
        password2  = request.POST.get('password2', '')

        errors = {}
        if not first_name:
            errors['first_name'] = 'First name is required.'
        if not email:
            errors['email'] = 'Email is required.'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'This email is already registered.'
        if not username:
            errors['username'] = 'Username is required.'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'Username already taken.'
        if len(password1) < 8:
            errors['password1'] = 'Password must be at least 8 characters.'
        if password1 != password2:
            errors['password2'] = 'Passwords do not match.'

        if not errors:
            user = User.objects.create_user(
                email=email,
                username=username,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
            )
            login(request, user)
            messages.success(request, f'Welcome to Wale Computers, {user.first_name}! 🎉')
            return redirect('shop:home')

        return render(request, 'accounts/register.html', {
            'errors': errors,
            'form_data': request.POST,
        })

    return render(request, 'accounts/register.html')


# ── Login ───────────────────────────────────────────────
def user_login(request):
    if request.user.is_authenticated:
        return redirect('shop:home')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember')

        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            if not remember:
                request.session.set_expiry(0)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect(request.GET.get('next', 'shop:home'))
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html', {'next': request.GET.get('next', '')})


# ── Logout ──────────────────────────────────────────────
@require_POST
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('shop:home')


# ── Profile ─────────────────────────────────────────────
@login_required
def profile(request):
    profile_obj = request.user.profile
    if request.method == 'POST':
        u = request.user
        u.first_name = request.POST.get('first_name', u.first_name)
        u.last_name  = request.POST.get('last_name', u.last_name)
        u.phone      = request.POST.get('phone', u.phone)
        u.bio        = request.POST.get('bio', u.bio)
        u.save()

        p = profile_obj
        p.county      = request.POST.get('county', p.county)
        p.address     = request.POST.get('address', p.address)
        p.city        = request.POST.get('city', p.city)
        p.mpesa_phone = request.POST.get('mpesa_phone', p.mpesa_phone)
        p.newsletter  = bool(request.POST.get('newsletter'))
        p.notifications = bool(request.POST.get('notifications'))
        if 'avatar' in request.FILES:
            p.avatar = request.FILES['avatar']
        p.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')

    orders = Order.objects.filter(user=request.user).order_by('-created_at')[:5]
    return render(request, 'accounts/profile.html', {
        'profile': profile_obj,
        'orders': orders,
    })


@login_required
def settings_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'change_password':
            from django.contrib.auth import update_session_auth_hash
            old_pw  = request.POST.get('old_password')
            new_pw1 = request.POST.get('new_password1')
            new_pw2 = request.POST.get('new_password2')
            if not request.user.check_password(old_pw):
                messages.error(request, 'Current password is incorrect.')
            elif new_pw1 != new_pw2:
                messages.error(request, 'New passwords do not match.')
            elif len(new_pw1) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
            else:
                request.user.set_password(new_pw1)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password updated successfully.')
        return redirect('accounts:settings')

    return render(request, 'accounts/settings.html')


@login_required
def orders(request):
    order_list = Order.objects.filter(user=request.user).prefetch_related('items__product')
    return render(request, 'accounts/orders.html', {'orders': order_list})