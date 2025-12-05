from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django.db import connection
from .serializers import (
    BlogViewsAnalyticsSerializer,
    BlogViewsAnalyticsResponseSerializer, TopAnalyticsSerializer, TopAnalyticsResponseSerializer,
    PerformanceAnalyticsResponseSerializer, PerformanceAnalyticsSerializer,
)
from .services import BlogViewsAnalyticsService

"""
Provides aggregated analytics showing how blog views are distributed across a chosen dimension 
(either by country or by viewer user), grouped over a selected time range (month, week, or year).
"""
class BlogViewsAnalyticsView(APIView):
    """
    API #1 — /analytics/blog-views/

    Groups blog views by country or user (viewer) with time bucketing.
    Returns: x = group key, y = number of blogs viewed, z = total views
    """

    def get(self, request):
        serializer = BlogViewsAnalyticsSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data

        start_date = validated_data.get('start_date')
        end_date = validated_data.get('end_date')

        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=180)

        filter_tree = validated_data.get('filter', {})
        service = BlogViewsAnalyticsService()
        raw_results = service.get_grouped_views(
            object_type=validated_data['object_type'],
            range_type=validated_data['range'],
            start_date=start_date,
            end_date=end_date,
            filter_tree=filter_tree,
            user=request.user
        )

        # Format response exactly as required: [{x, y, z}, ...]
        data_points = [
            {
                "x": str(item['group_key'] or 'Unknown'),
                "y": item['blogs_count'],
                "z": item['views_count'],
            }
            for item in raw_results
        ]

        data_points.sort(key=lambda x: x['z'], reverse=True)
        response_data = {
            "data": data_points,
            "meta": {
                "object_type": validated_data['object_type'],
                "range": validated_data['range'],
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "total_groups": len(data_points),
                "query_time_ms": self._get_query_time_ms(connection),
            }
        }

        response_serializer = BlogViewsAnalyticsResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def _auto_date_range(self, range_type: str):
        today = timezone.now().date()
        if range_type == 'week':
            # Last 52 weeks
            end_date = today - timedelta(days=today.weekday() + 1)
            start_date = end_date - timedelta(weeks=51)
        elif range_type == 'month':
            # Last 12 complete months
            end_date = today.replace(day=1) - timedelta(days=1)
            start_date = end_date - timedelta(days=365)
            start_date = start_date.replace(day=1)
        elif range_type == 'year':
            # Last 5 complete years
            end_date = today.replace(month=1, day=1) - timedelta(days=1)
            start_date = end_date.replace(year=end_date.year - 4, month=1, day=1)
        else:
            raise ValueError("Invalid range")

        return start_date, end_date

    def _get_query_time_ms(self, connection):
        if connection.queries:
            last_query = connection.queries[-1]
            return round(float(last_query.get('time', 0)) * 1000, 2)
        return None

"""
Returns the Top 10 entities (blogs, countries, or viewers) ranked by total number of views in a given time period.
"""
class TopAnalyticsView(APIView):
    def get(self, request):
        serializer = TopAnalyticsSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=400)

        data = serializer.validated_data

        # Auto date range fallback (last 90 days)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=89)

        service = BlogViewsAnalyticsService()
        results = service.get_top_10(
            top_type=data['top'],
            start_date=start_date,
            end_date=end_date,
            filter_tree=data.get('filter'),
        )

        response_data = {
            "data": results,
            "meta": {
                "top_type": data['top'],
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "total_returned": len(results)
            }
        }

        resp_serializer = TopAnalyticsResponseSerializer(response_data)
        return Response(resp_serializer.data)

"""
It is a time-series analytics dashboard that shows how performance evolves 
over time (day/week/month/year) for either all users or a specific author.
"""
class PerformanceAnalyticsView(APIView):
    def get(self, request):
        serializer = PerformanceAnalyticsSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=400)

        data = serializer.validated_data

        # Default: last 12 months
        if not data.get('start_date') or not data.get('end_date'):
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=180)
            data['start_date'] = start_date
            data['end_date'] = end_date

        service = BlogViewsAnalyticsService()
        results = service.get_performance_timeseries(
            compare=data['compare'],
            user_id=data.get('user_id'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            filter_tree=data.get('filter'),
        )

        response = {
            "data": results,
            "meta": {
                "compare": data['compare'],
                "user_id": data.get('user_id'),
                "period": {
                    "start": data['start_date'].isoformat(),
                    "end": (data['end_date'] or timezone.now().date()).isoformat(),
                }
            }
        }

        resp_serializer = PerformanceAnalyticsResponseSerializer(response)
        return Response(resp_serializer.data)