from django.db.models import Count, Q
from django.db.models.functions import TruncWeek, TruncMonth, TruncYear, TruncDay
from django.utils import timezone
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from .models import BlogView, Blog

class DynamicFilterEngine:
    """Reusable filter → Q object parser (used by ALL 3 APIs)"""
    ALLOWED_FIELDS = {
        'country': 'country',
        'user.id': 'user__id',
        'user.username': 'user__username',
        'blog.id': 'blog__id',
        'blog.slug': 'blog__slug',
        'blog.title': 'blog__title',
        'blog.author.id': 'blog__author__id',
        'blog.author.username': 'blog__author__username',
        'viewed_at': 'viewed_at',
    }

    OP_MAP = {
        'eq': lambda f, v: Q(**{f: v}),
        'neq': lambda f, v: ~Q(**{f: v}),
        'in': lambda f, v: Q(**{f"{f}__in": v}),
        'not_in': lambda f, v: ~Q(**{f"{f}__in": v}),
        'gt': lambda f, v: Q(**{f"__gt": v}),
        'gte': lambda f, v: Q(**{f"__gte": v}),
        'lt': lambda f, v: Q(**{f"__lt": v}),
        'lte': lambda f, v: Q(**{f"__lte": v}),
    }

    @classmethod
    def build_q_from_filter(cls, filter_tree: Dict) -> Q:
        if not filter_tree:
            return Q()

        def parse_node(node) -> Q:
            if not isinstance(node, dict) or len(node) != 1:
                raise ValueError("Invalid filter node")

            key, value = next(iter(node.items()))

            if key == 'and':
                return Q(*[parse_node(n) for n in value])
            if key == 'or':
                return Q(*[parse_node(n) for n in value], _connector=Q.OR)
            if key == 'not':
                return ~parse_node(value)

            # Leaf condition
            cond = value if key == 'field' else node
            field = cond['field']
            op = cond['op']
            val = cond['value']

            if field not in cls.ALLOWED_FIELDS:
                raise ValueError(f"Field not allowed: {field}")

            django_field = cls.ALLOWED_FIELDS[field]
            if op not in cls.OP_MAP:
                raise ValueError(f"Invalid operator: {op}")

            return cls.OP_MAP[op](django_field, val)

        return parse_node(filter_tree)


class BlogViewsAnalyticsService:
    """
    ONE SERVICE → ALL 3 APIs
    Reusable, testable, N+1-proof
    """

    def get_grouped_views(
            self,
            object_type: str,
            range_type: str,
            start_date,
            end_date,
            filter_tree: Optional[Dict] = None,
            user=None,
    ) -> List[Dict]:
        queryset = BlogView.objects.all()
        queryset = queryset.filter(viewed_at__date__gte=start_date, viewed_at__date__lte=end_date)

        if filter_tree:
            queryset = queryset.filter(DynamicFilterEngine.build_q_from_filter(filter_tree))

        if object_type == 'country':
            results = (
                queryset
                .values('country')
                .annotate(
                    blogs_count=Count('blog_id', distinct=True),
                    views_count=Count('id')
                )
                .filter(views_count__gt=0)
                .order_by('-views_count')
            )

            formatted = []
            for r in results:
                country = r['country'] or 'Unknown'
                if country == 'XX':
                    country = 'Unknown'
                formatted.append({
                    'group_key': country,
                    'blogs_count': r['blogs_count'],
                    'views_count': r['views_count'],
                })
            return formatted

        else:
            results = (
                queryset
                .values('user_id', 'user__username')
                .annotate(
                    blogs_count=Count('blog_id', distinct=True),
                    views_count=Count('id')
                )
                .filter(views_count__gt=0)
                .order_by('-views_count')
            )

            formatted = []
            for r in results:
                if r['user_id'] is None:
                    x = 'Anonymous'
                else:
                    x = r['user__username'] or f"user_{r['user_id']}"
                formatted.append({
                    'group_key': x,
                    'blogs_count': r['blogs_count'],
                    'views_count': r['views_count'],
                })
            return formatted

    def get_top_10(
        self,
        top_type: str,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        filter_tree: Optional[Dict] = None,
    ) -> List[Dict]:
        queryset = BlogView.objects.all()

        if start_date:
            queryset = queryset.filter(viewed_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(viewed_at__date__lte=end_date)
        if filter_tree:
            queryset = queryset.filter(DynamicFilterEngine.build_q_from_filter(filter_tree))

        if top_type == 'blog':
            results = (
                queryset.values('blog__title', 'blog__slug', 'blog__author__username')
                .annotate(total_views=Count('id'))
                .order_by('-total_views')[:10]
            )
            return [
                {
                    "x": r['blog__title'] or r['blog__slug'],
                    "y": r['total_views'],
                    "z": r['blog__author__username'] or "unknown",
                }
                for r in results
            ]

        elif top_type == 'country':
            results = (
                queryset.values('country')
                .annotate(total_views=Count('id'))
                .order_by('-total_views')[:10]
            )
            return [
                {
                    "x": r['country'] if r['country'] != 'XX' else 'Unknown',
                    "y": r['total_views'],
                    "z": None,
                }
                for r in results
            ]

        elif top_type == 'user':
            results = (
                queryset.values('user_id', 'user__username')
                .annotate(total_views=Count('id'))
                .filter(user_id__isnull=False)
                .order_by('-total_views')[:10]
            )
            return [
                {
                    "x": r['user__username'] or f"user_{r['user_id']}",
                    "y": r['total_views'],
                    "z": None,
                }
                for r in results
            ]

        raise ValueError(f"Invalid top_type: {top_type}")

    def get_performance_timeseries(
            self,
            compare: str,
            user_id: Optional[int] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            filter_tree: Optional[Dict] = None,
    ) -> List[Dict]:

        end_date = end_date or timezone.now().date()
        start_date = start_date or end_date - timedelta(days=180)

        trunc_func = {'day': TruncDay, 'week': TruncWeek, 'month': TruncMonth, 'year': TruncYear}[compare]

        # Views
        qs = BlogView.objects.filter(viewed_at__date__gte=start_date, viewed_at__date__lte=end_date)
        if user_id:
            qs = qs.filter(blog__author_id=user_id)
        if filter_tree:
            qs = qs.filter(DynamicFilterEngine.build_q_from_filter(filter_tree))

        views = qs.annotate(p=trunc_func('viewed_at')).values('p').annotate(y=Count('id')).order_by('p')
        views_map = {v['p'].date(): v['y'] for v in views}

        # Blogs created
        bqs = Blog.objects.filter(published_at__date__gte=start_date, published_at__date__lte=end_date,
                                  is_published=True)
        if user_id:
            bqs = bqs.filter(author_id=user_id)
        blogs = bqs.annotate(p=trunc_func('published_at')).values('p').annotate(c=Count('id'))
        blogs_map = {b['p'].date(): b['c'] for b in blogs}

        # Generate periods
        current = start_date.replace(day=1) if compare != 'day' else start_date
        result = []
        prev = None

        while current <= end_date:
            views_count = views_map.get(current, 0)
            blogs_count = blogs_map.get(current, 0)

            if compare == 'month':
                label = current.strftime("%Y %b")
            elif compare == 'day':
                label = current.strftime("%Y %b %d")
            elif compare == 'week':
                label = f"W{current.isocalendar()[1]} {current.year}"
            else:
                label = str(current.year)

            x = f"{label} (Blogs: {blogs_count})"

            if prev is None:
                z = "N/A"
            elif prev == 0:
                z = "+∞" if views_count > 0 else "N/A"
            else:
                growth = (views_count - prev) / prev * 100
                z = f"{growth:+.0f}%" if abs(growth) >= 5 else f"{growth:+.1f}%"

            result.append({"x": x, "y": views_count, "z": z})
            prev = views_count

            if compare == 'day':
                current += timedelta(days=1)
            elif compare == 'week':
                current += timedelta(weeks=1)
            elif compare == 'month':
                month = current.month + 1
                year = current.year + (month > 12)
                current = current.replace(year=year, month=(month - 1) % 12 + 1, day=1)
            else:
                current = current.replace(year=current.year + 1)

        return result