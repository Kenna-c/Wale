def global_context(request):
    context = {}
    if request.user.is_authenticated:
        from shop.models import Favorite
        from payments.models import Cart
        context['favorites_count'] = Favorite.objects.filter(user=request.user).count()
        try:
            cart = request.user.cart
            context['cart_count'] = cart.item_count
        except Exception:
            context['cart_count'] = 0
    return context