from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse


class User(AbstractUser):
    email      = models.EmailField(unique=True)
    phone      = models.CharField(max_length=20, blank=True)
    bio        = models.TextField(max_length=500, blank=True)
    is_verified= models.BooleanField(default=False)
    date_joined= models.DateTimeField(auto_now_add=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='wale_user_set',
        related_query_name='wale_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='wale_user_set',
        related_query_name='wale_user',
    )

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.get_full_name() or self.email

    def get_absolute_url(self):
        return reverse('accounts:profile')

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        fn = (self.first_name[:1] + self.last_name[:1]).upper()
        return fn if fn.strip() else self.username[:2].upper()


class Profile(models.Model):
    COUNTY_CHOICES = [
        ('nairobi',   'Nairobi'),
        ('mombasa',   'Mombasa'),
        ('kisumu',    'Kisumu'),
        ('nakuru',    'Nakuru'),
        ('eldoret',   'Eldoret'),
        ('thika',     'Thika'),
        ('other',     'Other'),
    ]

    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar           = models.ImageField(upload_to='avatars/', blank=True, null=True)
    county           = models.CharField(max_length=60, choices=COUNTY_CHOICES, blank=True)
    address          = models.TextField(blank=True)
    city             = models.CharField(max_length=80, blank=True)
    mpesa_phone      = models.CharField(max_length=15, blank=True, help_text="M-Pesa registered number")
    newsletter       = models.BooleanField(default=True)
    notifications    = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile – {self.user}"

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None  # fallback to initials in template


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()