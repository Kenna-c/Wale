from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from .models import Post, PostLike, Comment, ChatRoom, ChatMessage


# ── Feed ────────────────────────────────────────────────
def feed(request):
    qs = Post.objects.filter(is_approved=True).select_related('author__profile')

    post_type = request.GET.get('type')
    if post_type:
        qs = qs.filter(post_type=post_type)

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page'))

    rooms = ChatRoom.objects.filter(is_public=True)[:5]

    # Mark liked posts
    liked_ids = set()
    if request.user.is_authenticated:
        liked_ids = set(
            PostLike.objects.filter(user=request.user).values_list('post_id', flat=True)
        )

    # Ensure we don't attempt to access missing profile/avatar files in templates.
    # (e.g. when a user has a profile record but the image file is missing)
    for post in page:
        avatar_url = None
        try:
            avatar = post.author.profile.avatar
            if avatar:
                avatar_url = avatar.url
        except Exception:
            avatar_url = None
        setattr(post, 'author_avatar_url', avatar_url)

    return render(request, 'community/feed.html', {
        'posts': page,
        'rooms': rooms,
        'liked_ids': liked_ids,
        'active_type': post_type,
    })


# ── Create Post ─────────────────────────────────────────
@login_required
def create_post(request):
    from shop.models import Product
    if request.method == 'POST':
        title      = request.POST.get('title', '').strip()
        body       = request.POST.get('body', '').strip()
        post_type  = request.POST.get('post_type', 'discussion')
        tags       = request.POST.get('tags', '').strip()
        product_id = request.POST.get('product_tag')

        if not title or not body:
            messages.error(request, 'Title and content are required.')
        else:
            post = Post(
                author=request.user,
                title=title,
                body=body,
                post_type=post_type,
                tags=tags,
            )
            if product_id:
                try:
                    post.product_tag = Product.objects.get(pk=product_id)
                except Product.DoesNotExist:
                    pass
            if 'image' in request.FILES:
                post.image = request.FILES['image']
            post.save()
            messages.success(request, 'Your post has been published!')
            return redirect('community:post_detail', pk=post.pk)

    products = Product.objects.filter(is_active=True).only('id', 'name')
    return render(request, 'community/create_post.html', {'products': products})


# ── Post Detail ─────────────────────────────────────────
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk, is_approved=True)
    Post.objects.filter(pk=pk).update(views=post.views + 1)
    comments  = post.comments.filter(is_approved=True, parent=None).select_related('author__profile').prefetch_related('replies__author__profile')
    is_liked  = False
    if request.user.is_authenticated:
        is_liked = PostLike.objects.filter(user=request.user, post=post).exists()

    if request.method == 'POST' and request.user.is_authenticated:
        body      = request.POST.get('body', '').strip()
        parent_id = request.POST.get('parent_id')
        if body:
            Comment.objects.create(
                post=post,
                author=request.user,
                body=body,
                parent_id=parent_id if parent_id else None,
            )
            messages.success(request, 'Comment added!')
            return redirect('community:post_detail', pk=pk)

    return render(request, 'community/post_detail.html', {
        'post': post,
        'comments': comments,
        'is_liked': is_liked,
    })


# ── Like Post ───────────────────────────────────────────
@login_required
@require_POST
def like_post(request, pk):
    post  = get_object_or_404(Post, pk=pk)
    like, created = PostLike.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True

    return JsonResponse({'liked': liked, 'count': post.like_count})


# ── Chat ────────────────────────────────────────────────
@login_required
def chat_list(request):
    rooms = ChatRoom.objects.filter(is_public=True)
    return render(request, 'community/chat_list.html', {'rooms': rooms})


@login_required
def chat_room(request, slug):
    room     = get_object_or_404(ChatRoom, slug=slug, is_public=True)
    messages_qs = room.messages.filter(is_deleted=False).select_related('sender__profile').order_by('-created_at')[:60]
    messages_qs = reversed(list(messages_qs))  # chronological order

    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            ChatMessage.objects.create(room=room, sender=request.user, body=body)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok'})
            return redirect('community:chat', slug=slug)

    return render(request, 'community/chat.html', {
        'room': room,
        'chat_messages': messages_qs,
    })