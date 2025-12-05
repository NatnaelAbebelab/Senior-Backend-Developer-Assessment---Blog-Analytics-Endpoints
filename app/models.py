from django.db import models
from django.contrib.auth.models import User

class Blog(models.Model):
    id = models.BigAutoField(primary_key=True)
    slug = models.SlugField(unique=True, max_length=200)
    title = models.CharField(max_length=300)
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='blogs'
    )
    published_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['author', 'published_at']),
            models.Index(fields=['published_at']),
        ]

    def __str__(self):
        return self.title


class BlogView(models.Model):
    """
    One row per view (can scale to hundreds of millions) => every single time someone reads a blog post.
    This is the main analytics table.
    """
    id = models.BigAutoField(primary_key=True)
    blog = models.ForeignKey(
        Blog, on_delete=models.CASCADE, related_name='views'
    )
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='blog_views'
    )
    country = models.CharField(
        max_length=2,
        default='XX',
        db_index=True
    )
    viewed_at = models.DateTimeField(db_index=True, auto_now_add=True)
    session_id = models.CharField(max_length=40, null=True, blank=True, db_index=True)

    class Meta:
        indexes = [
            # API #1: group by country/user + time range
            models.Index(fields=['viewed_at', 'country']),
            models.Index(fields=['viewed_at', 'user']),
            models.Index(fields=['country', 'viewed_at']),
            models.Index(fields=['user', 'viewed_at']),

            # API #2: top blogs/countries/users
            models.Index(fields=['blog', 'viewed_at']),

            # API #3: time-series performance
            models.Index(fields=['viewed_at']),
        ]

    def __str__(self):
        return f"View {self.blog.title} by {self.user or 'Anonymous'} from {self.country}"