from rest_framework import serializers

class PublicLinkRequestSerializer(serializers.Serializer):
    ttl_days = serializers.IntegerField(required=False, default=30, min_value=1, max_value=365)

class PublicLinkResponseSerializer(serializers.Serializer):
    tracking_no = serializers.CharField()
    expires_at = serializers.DateTimeField()
    url = serializers.CharField()
