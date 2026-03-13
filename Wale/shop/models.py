from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Category(models.Model):
    name        = models.CharField(max_length=120)
    slug        = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon        = models.CharField(max_length=60, blank=True, help_text="FontAwesome icon class e.g. fa-laptop")
    parent      = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children')
    is_active   = models.BooleanField(default=True)
    order       = models.PositiveSmallIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_list') + f'?category={self.slug}'


class Brand(models.Model):
    name    = models.CharField(max_length=100)
    slug    = models.SlugField(unique=True, blank=True)
    logo    = models.ImageField(upload_to='brands/', blank=True, null=True)
    website = models.URLField(blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    CONDITION_CHOICES = [
        ('new',        'New'),
        ('refurb',     'Refurbished'),
        ('open_box',   'Open Box'),
    ]

    name           = models.CharField(max_length=250)
    slug           = models.SlugField(unique=True, blank=True, max_length=280)
    sku            = models.CharField(max_length=60, unique=True, blank=True)
    category       = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand          = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    description    = models.TextField()
    short_desc     = models.CharField(max_length=300, blank=True)
    price          = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         help_text="Original / crossed-out price")
    stock          = models.PositiveIntegerField(default=0)
    condition      = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    is_active      = models.BooleanField(default=True)
    is_featured    = models.BooleanField(default=False)
    weight_kg      = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    specs          = models.JSONField(default=dict, blank=True,
                                      help_text='{"RAM":"16GB","Storage":"512GB SSD",...}')
    tags           = models.CharField(max_length=300, blank=True, help_text="Comma-separated tags")
    views          = models.PositiveIntegerField(default=0)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            import uuid
            self.sku = f"WC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', kwargs={'slug': self.slug})

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        return img or self.images.first()

    @property
    def discount_percent(self):
        if self.compare_price and self.compare_price > self.price:
            return int(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0

    @property
    def average_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if reviews.exists():
            return round(reviews.aggregate(models.Avg('rating'))['rating__avg'], 1)
        return 0

    @property
    def review_count(self):
        return self.reviews.filter(is_approved=True).count()

    @property
    def in_stock(self):
        return self.stock > 0


class ProductImage(models.Model):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image      = models.ImageField(upload_to='products/')
    alt_text   = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order      = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.product.name} – image {self.order}"


class Favorite(models.Model):
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} ♥ {self.product.name}"


class Review(models.Model):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating     = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title      = models.CharField(max_length=150)
    body       = models.TextField()
    is_approved= models.BooleanField(default=True)
    is_verified= models.BooleanField(default=False, help_text="Purchased from Wale")
    helpful    = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} rated {self.product.name} {self.rating}★"

    @property
    def star_range(self):
        return range(self.rating)

    @property
    def empty_star_range(self):
        return range(5 - self.rating)