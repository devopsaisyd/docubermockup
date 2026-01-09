from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.geo import haversine_m


@dataclass(frozen=True)
class EtaResult:
    eta_minutes: int | None
    distance_m: int


async def distance_matrix_eta(
    *,
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> EtaResult:
    if not settings.google_maps_api_key:
        d = haversine_m(origin_lat, origin_lng, dest_lat, dest_lng)
        # conservative city speed ~ 20km/h + 3 mins fixed overhead
        eta = int(round((d / 1000) / 20 * 60 + 3))
        return EtaResult(eta_minutes=eta, distance_m=int(d))

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{origin_lat},{origin_lng}",
        "destinations": f"{dest_lat},{dest_lng}",
        "key": settings.google_maps_api_key,
        "mode": "driving",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    try:
        el = data["rows"][0]["elements"][0]
        distance_m = int(el["distance"]["value"])
        duration_s = int(el["duration_in_traffic"]["value"] if "duration_in_traffic" in el else el["duration"]["value"])
        eta_minutes = int(round(duration_s / 60))
        return EtaResult(eta_minutes=eta_minutes, distance_m=distance_m)
    except Exception:
        d = haversine_m(origin_lat, origin_lng, dest_lat, dest_lng)
        return EtaResult(eta_minutes=None, distance_m=int(d))

