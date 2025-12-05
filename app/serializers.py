from rest_framework import serializers

class BlogViewsAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for API #1: /analytics/blog-views/
    Groups views by country or user with dynamic time range and filters.
    """
    object_type = serializers.ChoiceField(
        choices=['country', 'user'],
        required=True,
        help_text="Group results by 'country' or 'user' (viewer)"
    )

    range = serializers.ChoiceField(
        choices=['week', 'month', 'year'],
        required=True,
        help_text="Time: week | month | year"
    )

    start_date = serializers.DateField(
        required=False,
        default=None,
        help_text="Inclusive start date (YYYY-MM-DD). Defaults to range-based auto"
    )

    end_date = serializers.DateField(
        required=False,
        default=None,
        help_text="Inclusive end date (YYYY-MM-DD). Defaults to today"
    )

    filter = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Filter with and/or/not logic"
    )

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')

        # If no dates provided → we'll auto-calculate based on `range`
        if not start and not end:
            return data

        if start and end and start > end:
            raise serializers.ValidationError(
                "start_date cannot be after end_date"
            )

        # Max allowed range: 5 years (prevents accidental full-table scans)
        if start and end:
            if (end - start).days > 1825:  # ~5 years
                raise serializers.ValidationError(
                    "Date range cannot exceed 5 years"
                )

        return data

    def validate_filter(self, value):
        if not value:
            return {}

        allowed_ops = {'eq', 'neq', 'in', 'not_in', 'gt', 'gte', 'lt', 'lte'}
        allowed_keys = {'and', 'or', 'not', 'field', 'op', 'value'}

        def validate_node(node):
            if isinstance(node, dict):
                if len(node) != 1:
                    raise serializers.ValidationError(
                        "Each filter must have exactly one key (and/or/not/condition)"
                    )
                key = next(iter(node))
                if key not in allowed_keys:
                    raise serializers.ValidationError(f"Invalid filter key: {key}")
                if key in ('and', 'or'):
                    if not isinstance(node[key], list):
                        raise serializers.ValidationError(f"{key} must contain a list")
                    for item in node[key]:
                        validate_node(item)
                elif key == 'not':
                    validate_node(node[key])
                else:  # condition leaf
                    cond = node[key] if key == 'value' else node
                    if not all(k in cond for k in ('field', 'op', 'value')):
                        raise serializers.ValidationError(
                            "Condition must have field, op, value"
                        )
                    if cond['op'] not in allowed_ops:
                        raise serializers.ValidationError(f"Invalid op: {cond['op']}")
                    if cond['op'] in ('in', 'not_in') and not isinstance(cond['value'], list):
                        raise serializers.ValidationError(
                            f"value for {cond['op']} must be a list"
                        )
            else:
                raise serializers.ValidationError("Filter node must be a dict")
        try:
            validate_node(value)
        except Exception as e:
            raise serializers.ValidationError(f"Invalid filter structure: {e}")

        return value

# Response serializer — defines exact x, y, z structure
class BlogViewsDataPointSerializer(serializers.Serializer):
    x = serializers.CharField(max_length=100)
    y = serializers.IntegerField(min_value=0)
    z = serializers.IntegerField(min_value=0)

class BlogViewsAnalyticsResponseSerializer(serializers.Serializer):
    data = BlogViewsDataPointSerializer(many=True)
    meta = serializers.DictField(child=serializers.CharField(), required=False)

class TopAnalyticsSerializer(serializers.Serializer):
    top = serializers.ChoiceField(
        choices=['user', 'country', 'blog'],
        required=True,
        help_text="Leaderboard type: user (viewer) | country | blog"
    )

    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    filter = serializers.JSONField(required=False, default=dict)

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        if start and end and start > end:
            raise serializers.ValidationError("start_date cannot be after end_date")
        return data

class TopAnalyticsResponseSerializer(serializers.Serializer):
    data = serializers.ListField(child=serializers.DictField())
    meta = serializers.DictField(required=False)

class PerformanceAnalyticsSerializer(serializers.Serializer):
    compare = serializers.ChoiceField(
        choices=['day', 'week', 'month', 'year'],
        required=True,
        help_text="Time bucket for comparison"
    )
    user_id = serializers.IntegerField(required=False, allow_null=True,
        help_text="Optional: filter performance for one author only")
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    filter = serializers.JSONField(required=False, default=dict)

    def validate(self, data):
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError("start_date cannot be after end_date")
        return data

class PerformanceDataPointSerializer(serializers.Serializer):
    x = serializers.CharField()
    y = serializers.IntegerField(min_value=0)
    z = serializers.CharField()

class PerformanceAnalyticsResponseSerializer(serializers.Serializer):
    data = PerformanceDataPointSerializer(many=True)
    meta = serializers.DictField()