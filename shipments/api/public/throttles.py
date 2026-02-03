# shipments/api/public/throttles.py
from rest_framework.throttling import SimpleRateThrottle

class PublicTrackThrottle(SimpleRateThrottle):
    scope = "public_track"

    def get_cache_key(self, request, view):
        # Rate limit per-IP
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
