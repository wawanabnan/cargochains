from rest_framework import serializers

class ShipmentEventPublicSerializer(serializers.Serializer):
    code = serializers.CharField()
    event_time = serializers.DateTimeField()
    location_text = serializers.CharField(allow_blank=True, required=False)
    note = serializers.CharField(allow_blank=True, required=False)

class PublicTrackingResponseSerializer(serializers.Serializer):
    tracking_no = serializers.CharField()
    status = serializers.CharField()
    timeline = ShipmentEventPublicSerializer(many=True)
