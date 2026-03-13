from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Product, Category, Brand, Favorite, Review


# ── Home 
def home(request):
    featured   = Product.objects.filter(is_active=True, is_featured=True)[:8]
    categories = Category.objects.filter(is_active=True, parent=None)[:8]
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    top_rated = (
        Product.objects.filter(is_active=True)
        .annotate(avg_rating=Avg('reviews__rating'), num_reviews=Count('reviews'))
        .filter(num_reviews__gt=0)
        .order_by('-avg_rating')[:8]
    )
    return render(request, 'shop/home.html', {
        'featured': featured,
        'categories': categories,
        'new_arrivals': new_arrivals,
        'top_rated': top_rated,
    })


# ── Product List / Search ───────────────────────────────
def product_list(request):
    qs = Product.objects.filter(is_active=True).select_related('category', 'brand')
    categories = Category.objects.filter(is_active=True)
    brands     = Brand.objects.all()

    # Filters
    category_slug = request.GET.get('category')
    brand_slug    = request.GET.get('brand')
    condition     = request.GET.get('condition')
    min_price     = request.GET.get('min_price')
    max_price     = request.GET.get('max_price')
    sort          = request.GET.get('sort', '-created_at')

    active_category = None
    if category_slug:
        active_category = get_object_or_404(Category, slug=category_slug)
        qs = qs.filter(category=active_category)
    if brand_slug:
        qs = qs.filter(brand__slug=brand_slug)
    if condition:
        qs = qs.filter(condition=condition)
    if min_price:
        qs = qs.filter(price__gte=min_price)
    if max_price:
        qs = qs.filter(price__lte=max_price)

    SORT_MAP = {
        '-created_at': '-created_at',
        'price_asc':   'price',
        'price_desc':  '-price',
        'popular':     '-views',
        'rating':      '-avg_rating',
    }
    if sort == 'rating':
        qs = qs.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    else:
        qs = qs.order_by(SORT_MAP.get(sort, '-created_at'))

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'shop/product_list.html', {
        'products': page,
        'categories': categories,
        'brands': brands,
        'active_category': active_category,
        'sort': sort,
        'filters': {
            'category': category_slug,
            'brand': brand_slug,
            'condition': condition,
            'min_price': min_price,
            'max_price': max_price,
        },
    })


def search(request):
    q  = request.GET.get('q', '').strip()
    qs = Product.objects.filter(is_active=True)
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(brand__name__icontains=q) |
            Q(category__name__icontains=q) |
            Q(tags__icontains=q)
        )
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'shop/search.html', {'products': page, 'query': q})


# ── Product Detail ──────────────────────────────────────
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)

    # Increment views
    Product.objects.filter(pk=product.pk).update(views=product.views + 1)

    reviews  = product.reviews.filter(is_approved=True).select_related('user__profile')
    related  = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(pk=product.pk)[:6]

    is_favorited = False
    user_review  = None
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, product=product).exists()
        user_review  = reviews.filter(user=request.user).first()

    # Rating distribution
    rating_dist = {i: reviews.filter(rating=i).count() for i in range(5, 0, -1)}

    # Review submission
    if request.method == 'POST' and request.user.is_authenticated:
        if not user_review:
            rating = int(request.POST.get('rating', 5))
            title  = request.POST.get('title', '').strip()
            body   = request.POST.get('body', '').strip()
            if title and body:
                Review.objects.create(
                    product=product,
                    user=request.user,
                    rating=rating,
                    title=title,
                    body=body,
                )
                messages.success(request, 'Your review has been submitted!')
                return redirect(product.get_absolute_url())

    return render(request, 'shop/product_detail.html', {
        'product':      product,
        'reviews':      reviews,
        'related':      related,
        'is_favorited': is_favorited,
        'user_review':  user_review,
        'rating_dist':  rating_dist,
    })


# ── Favorites ───────────────────────────────────────────
@login_required
def favorites(request):
    favs = Favorite.objects.filter(user=request.user).select_related('product__category')
    return render(request, 'shop/favorites.html', {'favorites': favs})


@login_required
@require_POST
def toggle_favorite(request, pk):
    product = get_object_or_404(Product, pk=pk)
    fav, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if not created:
        fav.delete()
        added = False
    else:
        added = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'added': added, 'count': Favorite.objects.filter(user=request.user).count()})

    msg = f"Added '{product.name}' to favorites" if added else f"Removed from favorites"
    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'shop:favorites'))