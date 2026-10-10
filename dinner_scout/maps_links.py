"""Google Maps links that open the Maps app on a phone, and the QR code that carries one.

Maps URLs (https://developers.google.com/maps/documentation/urls/get-started, checked 2026-10-09): no API key;
on Android and iOS they open the Google Maps app when it is installed, a browser otherwise. A place ID parameter
must travel with its name. With no origin, Maps routes from wherever the phone is, which is what we want: the
person scanning the code is in the room.
"""
from urllib.parse import urlencode

import qrcode
import qrcode.image.svg

TRAVEL_MODES = ("walking", "transit", "driving", "bicycling")


def directions_url(name: str, place_id: str = "", travel_mode: str = "walking") -> str:
    params = {"api": "1", "destination": name, "travelmode": travel_mode if travel_mode in TRAVEL_MODES else "walking"}
    if place_id:
        params["destination_place_id"] = place_id
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def qr_svg(url: str) -> str:
    """An SVG QR code (black modules, no background) the page can drop straight into the DOM."""
    img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, border=2)
    return img.to_string(encoding="unicode")
