from pathlib import Path
import math

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render


# Path to your Excel file:  BmoreLine/input_data/1109 Upload_geocoded.xlsx
XLSX_PATH = Path(settings.BASE_DIR) /"input_data" / "1109 Upload_geocoded.xlsx"


def _to_float(x):
    """Safe float conversion; returns None if not a usable number."""
    try:
        if x is None:
            return None
        f = float(x)
        if math.isnan(f):
            return None
        return f
    except Exception:
        return None


def _load_resources_from_xlsx():
    """
    Load resources from the Excel file and return (resources_list, diagnostics_dict).

    Expected headers (case / spacing insensitive; these are what you told me earlier):
      ID
      Address
      Phone Number
      Email
      Name of Service
      Restrictions of Service
      Days of Service
      Cateogry of Help
      Description
      link to site
      Legitimate place?
      called + confirmed?
      Reliability Rate 1-10
      Call experience
      Unnamed: 18
      Latitude
      Longitude
    """

    diag = {
        "path": str(XLSX_PATH),
        "exists": XLSX_PATH.exists(),
        "sheet_title": None,
        "headers": [],
        "parsed_rows": 0,
        "skipped_no_coords": 0,
        "bad_latlng": 0,
        "errors": [],
        "sample_row": {},
    }

    resources = []

    if not XLSX_PATH.exists():
        diag["errors"].append("File not found")
        return resources, diag

    try:
        from openpyxl import load_workbook
    except ImportError:
        diag["errors"].append("openpyxl not installed (pip install openpyxl)")
        return resources, diag

    try:
        wb = load_workbook(filename=str(XLSX_PATH), data_only=True)
        ws = wb.active
        diag["sheet_title"] = ws.title

        # Header row
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        headers = [h or "" for h in header_row]
        diag["headers"] = headers

        def norm(s):
            return " ".join(str(s).strip().lower().split()) if s is not None else ""

        header_map = {norm(h): idx for idx, h in enumerate(headers)}

        def grab(row, *names, default=""):
            """Pull a cell by any of the given header names."""
            for n in names:
                idx = header_map.get(norm(n))
                if idx is not None and idx < len(row):
                    val = row[idx]
                    if val is not None:
                        return val
            return default

        def to_bool_flag(v):
            if v is None:
                return None
            s = str(v).strip().lower()
            if s in {"yes", "y", "true", "1"}:
                return True
            if s in {"no", "n", "false", "0"}:
                return False
            return None  # unknown / not filled

        for row in ws.iter_rows(min_row=2, values_only=True):
            name = str(grab(row, "Name of Service", "Name", default="")).strip()
            address = str(grab(row, "Address", default="")).strip()
            phone = str(grab(row, "Phone Number", "Phone", default="")).strip()
            email = str(grab(row, "Email", default="")).strip()
            category = str(
                grab(row, "Cateogry of Help", "Category of Help", "Category", default="")
            ).strip() or "Uncategorized"
            desc = str(grab(row, "Description", default="")).strip()
            restrictions = str(grab(row, "Restrictions of Service", default="")).strip()
            days = str(grab(row, "Days of Service", default="")).strip()
            link = str(
                grab(row, "link to site", "Website", "Link", default="")
            ).strip()

            legit_raw = grab(row, "Legitimate place?", "Legitimate place ?", default="")
            confirmed_raw = grab(row, "called + confirmed?", "called + confirmed ?", default="")

            reliability_raw = str(
                grab(row, "Reliability Rate 1-10", "Reliability Rate 1–10", "Reliability", default="")
            ).strip()
            reliability = reliability_raw if reliability_raw not in {"", "nan", "none"} else "na"

            call_exp = str(grab(row, "Call experience", default="")).strip()
            extra = str(grab(row, "Unnamed: 18", default="")).strip()
            call_notes = " | ".join([x for x in [call_exp, extra] if x])

            lat_raw = grab(row, "Latitude", "Lat", default=None)
            lng_raw = grab(row, "Longitude", "Lng", "Long", default=None)

            lat = _to_float(lat_raw)
            lng = _to_float(lng_raw)

            # Skip rows without usable coordinates
            if lat is None or lng is None:
                diag["skipped_no_coords"] += 1
                continue

            # Filter obviously invalid coordinates
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                diag["bad_latlng"] += 1
                continue

            rid = grab(row, "ID", "id", default=None)
            if rid is None or str(rid).strip() == "":
                rid = len(resources) + 1

            res = {
                "id": rid,
                "name": name or "Unnamed resource",
                "lat": lat,
                "lng": lng,
                "category": category,
                "phone_number": phone,
                "address": address,
                "email": email,
                "description": desc,
                "restrictions": restrictions,
                "days": days,
                "link": link,
                "legit": to_bool_flag(legit_raw),
                "confirmed": to_bool_flag(confirmed_raw),
                "reliability": reliability,
                "call_notes": call_notes,
            }
            resources.append(res)

        diag["parsed_rows"] = len(resources)
        if resources:
            diag["sample_row"] = resources[0]

    except Exception as e:
        diag["errors"].append(f"{type(e).__name__}: {e}")

    return resources, diag


def resources_map(request):
    """Main map view – loads data from Excel and passes it into the template."""
    resources, diag = _load_resources_from_xlsx()

    # Quick debug view: /resources_map/?debug=1
    if request.GET.get("debug") == "1":
        return HttpResponse(
            f"DEBUG – Excel path: {diag['path']}\n"
            f"Exists: {diag['exists']}\n"
            f"Sheet: {diag['sheet_title']}\n"
            f"Headers: {diag['headers']}\n"
            f"Parsed rows (with coords): {diag['parsed_rows']}\n"
            f"Skipped (no coords): {diag['skipped_no_coords']}\n"
            f"Bad lat/lng: {diag['bad_latlng']}\n"
            f"Errors: {diag['errors']}\n"
            f"Sample row: {diag['sample_row']}"
            .replace("\n", "<br>")
        )

    # Normal map render
    return render(request, "map_home.html", {"resources": resources})


def home_page(request):
    return render(request, "home.html")


# debug endpoint still available
def ping(request):
    return HttpResponse("pong")
