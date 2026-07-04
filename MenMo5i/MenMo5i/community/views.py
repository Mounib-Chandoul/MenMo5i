from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Exists, OuterRef, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from generation_engine.models import DesignSession
from .models import Follow, Like


CATEGORY_ORDER = [
    ('all', 'All'),
    (DesignSession.Category.ABSTRACT, 'Abstract'),
    (DesignSession.Category.TYPOGRAPHY, 'Typography'),
    (DesignSession.Category.ILLUSTRATION, 'Illustration'),
    (DesignSession.Category.TECHWEAR, 'Techwear'),
    (DesignSession.Category.MINIMAL, 'Minimal'),
]


def community_gallery_view(request):
    category = (request.GET.get('category') or 'all').lower()
    show_following = request.GET.get('feed') == 'following'
    search_query = (request.GET.get('q') or '').strip()

    sessions = DesignSession.objects.filter(is_public=True).select_related('user').prefetch_related('artworks')

    if show_following and request.user.is_authenticated:
        following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        sessions = sessions.filter(user_id__in=following_ids)

    if search_query:
        sessions = sessions.filter(
            Q(raw_prompt__icontains=search_query) | Q(user__username__icontains=search_query)
        )

    if category != 'all':
        valid_categories = {key for key, _ in CATEGORY_ORDER if key != 'all'}
        if category in valid_categories:
            sessions = sessions.filter(category=category)
        else:
            return HttpResponseBadRequest('Invalid category')

    if request.user.is_authenticated:
        sessions = sessions.annotate(
            follower_count=Count('user__follower_links', distinct=True),
            is_following=Exists(Follow.objects.filter(follower=request.user, following=OuterRef('user'))),
            like_count=Count('artworks__likes', distinct=True),
            is_liked=Exists(
                Like.objects.filter(user=request.user, art__session=OuterRef('pk'))
            ),
        )
        following_ids = set(Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
    else:
        sessions = sessions.annotate(
            follower_count=Count('user__follower_links', distinct=True),
            like_count=Count('artworks__likes', distinct=True),
        )
        following_ids = set()

    sessions = sessions.order_by('-created_at')
    return render(request, 'community/gallery.html', {
        'sessions': sessions,
        'category': category,
        'category_tabs': CATEGORY_ORDER,
        'show_following': show_following,
        'following_ids': following_ids,
        'search_query': search_query,
    })


@login_required
def toggle_follow_view(request, user_id):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')

    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        messages.error(request, 'You cannot follow yourself.')
        return redirect(request.META.get('HTTP_REFERER') or reverse('community:gallery'))

    follow, created = Follow.objects.get_or_create(follower=request.user, following=target_user)
    if not created:
        follow.delete()
        messages.success(request, f'Unfollowed {target_user.username}.')
    else:
        messages.success(request, f'Now following {target_user.username}.')
    return redirect(request.META.get('HTTP_REFERER') or reverse('community:gallery'))


@login_required
def toggle_like_view(request, art_id):
    if request.method != 'POST':
        return HttpResponseBadRequest('POST required')

    from generation_engine.models import GeneratedArt
    art = get_object_or_404(GeneratedArt, id=art_id)
    like, created = Like.objects.get_or_create(user=request.user, art=art)
    if not created:
        like.delete()
    return redirect(request.META.get('HTTP_REFERER') or reverse('community:gallery'))
