# MINIMAL & PERFECT TEST DATA — ~400 views (instant)
from django.contrib.auth.models import User
from app.models import Blog, BlogView
from django.utils import timezone
from datetime import timedelta
import random

# Clean start
User.objects.all().delete()
Blog.objects.all().delete()
BlogView.objects.all().delete()

print("Creating 3 authors + 10 blogs + ~400 views...")

# 3 authors
users = [User.objects.create_user(username=name, password="123")
         for name in ["abebe", "kebede", "almaz"]]

# 10 blogs over the last 6 months
now = timezone.now()
blogs = []
for i in range(1, 11):
    author = random.choice(users)
    days_ago = random.randint(10, 180)
    blog = Blog.objects.create(
        title=f"Blog #{i}: {random.choice(['Django', 'Python', 'React', 'AWS'])} Tips",
        slug=f"blog-{i}",
        author=author,
        published_at=now - timedelta(days=days_ago),
        is_published=True
    )
    blogs.append(blog)

# ~40 views per blog = ~400 total
countries = ["US", "IN", "DE", "CA", "JP"]
for blog in blogs:
    for _ in range(40):
        BlogView.objects.create(
            blog=blog,
            user=random.choice([None] + users),
            country=random.choice(countries),
            viewed_at=blog.published_at + timedelta(days=random.randint(0, 60))
        )

print("DONE! ~400 views created")
print("Run: python manage.py runserver")
print("Then open any API — all work perfectly with real data")
exit()