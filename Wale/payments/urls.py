from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('cart/',                           views.cart,                  name='cart'),
    path('cart/add/<int:pk>/',              views.add_to_cart,           name='add_to_cart'),
    path('cart/update/<int:item_id>/',      views.update_cart,           name='update_cart'),
    path('checkout/',                       views.checkout,              name='checkout'),
    path('pay/<uuid:pk>/mpesa/',            views.mpesa_payment,         name='mpesa_payment'),
    path('pay/<uuid:pk>/confirmation/',     views.payment_confirmation,  name='payment_confirmation'),
    path('orders/<uuid:pk>/',               views.order_detail,          name='order_detail'),
]


