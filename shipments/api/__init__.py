# shipments/api/public/views.py
from rest_framework.views import APIView
from rest_framework.response import Response

class PublicTrackShipmentView(APIView):
    def get(self, request, tracking_no):
        return Response({"ok": True})
