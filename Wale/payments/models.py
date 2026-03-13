from django.db import models
from django.conf import settings
from django.urls import reverse
import uuid

User = settings.AUTH_USER_MODEL


class Cart(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart – {self.user}"

    @property
    def total(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart       = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product    = models.ForeignKey('shop.Product', on_delete=models.CASCADE)
    quantity   = models.PositiveSmallIntegerField(default=1)
    added_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity}× {self.product.name}"

    @property
    def subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending',    'Pending Payment'),
        ('confirming', 'Confirming Payment'),
        ('paid',       'Paid'),
        ('processing', 'Processing'),
        ('shipped',    'Shipped'),
        ('delivered',  'Delivered'),
        ('cancelled',  'Cancelled'),
        ('refunded',   'Refunded'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number   = models.CharField(max_length=20, unique=True, blank=True)
    user           = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mpesa')

    # Shipping
    full_name      = models.CharField(max_length=150)
    phone          = models.CharField(max_length=20)
    email          = models.EmailField()
    address        = models.TextField()
    city           = models.CharField(max_length=80)
    county         = models.CharField(max_length=60)

    # Totals
    subtotal       = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total          = models.DecimalField(max_digits=10, decimal_places=2)

    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            import random, string
            prefix = 'WC'
            suffix = ''.join(random.choices(string.digits, k=7))
            self.order_number = f"{prefix}{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_number} – {self.user}"

    def get_absolute_url(self):
        return reverse('payments:order_detail', kwargs={'pk': self.pk})


class OrderItem(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product    = models.ForeignKey('shop.Product', on_delete=models.PROTECT)
    quantity   = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}× {self.product.name}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class MpesaPayment(models.Model):
    """Stores M-Pesa manual confirmation details submitted by customer."""

    STATUS_CHOICES = [
        ('submitted',  'Submitted – Awaiting Review'),
        ('verified',   'Verified'),
        ('rejected',   'Rejected'),
    ]

    order              = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='mpesa_payment')
    mpesa_phone        = models.CharField(max_length=15, help_text="Phone used for M-Pesa e.g. 07XXXXXXXX")
    transaction_code   = models.CharField(max_length=20, help_text="M-Pesa confirmation code e.g. QHX12345AB")
    amount_paid        = models.DecimalField(max_digits=10, decimal_places=2)
    payment_screenshot = models.ImageField(upload_to='mpesa_proofs/', blank=True, null=True,
                                           help_text="Optional screenshot of M-Pesa confirmation")
    status             = models.CharField(max_length=15, choices=STATUS_CHOICES, default='submitted')
    admin_note         = models.TextField(blank=True)
    submitted_at       = models.DateTimeField(auto_now_add=True)
    verified_at        = models.DateTimeField(null=True, blank=True)
    verified_by        = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_payments'
    )

    def __str__(self):
        return f"M-Pesa {self.transaction_code} – {self.order.order_number}"

    PAYBILL      = "522522"
    ACCOUNT_NAME = "Wale Computers"
    TILL_NUMBER  = "5530150"     # 
