from django.urls import path
from .views import BlogViewsAnalyticsView, TopAnalyticsView, PerformanceAnalyticsView

urlpatterns = [
    path('analytics/blog-views/', BlogViewsAnalyticsView.as_view(), name='blog-views-analytics'),
    path('analytics/top/', TopAnalyticsView.as_view(), name='top-analytics'),
    path('analytics/performance/', PerformanceAnalyticsView.as_view(), name='performance-analytics'),
]