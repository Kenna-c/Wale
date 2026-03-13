from django.db import models
from django.conf import settings
from django.urls import reverse

User = settings.AUTH_USER_MODEL


class Post(models.Model):
    TYPE_CHOICES = [
        ('recommendation', 'Recommendation'),
        ('question',       'Question'),
        ('discussion',     'Discussion'),
        ('deal',           'Deal Alert'),
        ('review',         'Mini Review'),
    ]

    author      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    post_type   = models.CharField(max_length=20, choices=TYPE_CHOICES, default='discussion')
    title       = models.CharField(max_length=250)
    body        = models.TextField()
    product_tag = models.ForeignKey(
        'shop.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='community_posts'
    )
    tags        = models.CharField(max_length=300, blank=True)
    image       = models.ImageField(upload_to='community/', blank=True, null=True)
    is_pinned   = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    views       = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('community:post_detail', kwargs={'pk': self.pk})

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()

    @property
    def tag_list(self):
        return [t.strip() for t in self.tags.split(',') if t.strip()]


class PostLike(models.Model):
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')


class Comment(models.Model):
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    parent     = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    body       = models.TextField(max_length=1000)
    is_approved= models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author} on '{self.post}'"


class ChatRoom(models.Model):
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(unique=True)
    description = models.CharField(max_length=250, blank=True)
    is_public   = models.BooleanField(default=True)
    members     = models.ManyToManyField(User, related_name='chat_rooms', blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('community:chat', kwargs={'slug': self.slug})

    @property
    def online_count(self):
        return self.messages.filter(
            created_at__gte=models.functions.Now() - models.ExpressionWrapper(
                models.Value(5), output_field=models.DurationField()
            )
        ).values('sender').distinct().count()


class ChatMessage(models.Model):
    room       = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    body       = models.TextField(max_length=2000)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender}: {self.body[:50]}"