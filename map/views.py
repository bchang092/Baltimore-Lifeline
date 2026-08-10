from pathlib import Path
import math

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from .models import CommunityFeedback
from .triage import build_triage_result


# Path to your Excel file:  BmoreLine/input_data/1109 Upload_geocoded.xlsx
XLSX_PATH = Path(settings.BASE_DIR) /"input_data" / "03232026_Upload_geocoded.xlsx"


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
        "category_header": None,
        "category_header_checked": False,
        "consolidated_categories": [],
        "tag_columns_found": [],
        "tag_counts": {},
        "taglist_header": None,
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
        print("Detected headers:", headers)

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

        def first_matching_header(*names):
            for n in names:
                if norm(n) in header_map:
                    return n
            return None

        def to_bool_flag(v):
            if v is None:
                return None
            s = str(v).strip().lower()
            if s in {"yes", "y", "true", "1"}:
                return True
            if s in {"no", "n", "false", "0"}:
                return False
            return None  # unknown / not filled

        def is_truthy_tag(v):
            if v is None:
                return False
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return v != 0 and not math.isnan(v)
            s = str(v).strip().lower()
            if s in {"yes", "y", "true", "1", "x"}:
                return True
            if s in {"no", "n", "false", "0", ""}:
                return False
            return False

        def parse_tag_list(val):
            if val is None:
                return []
            s = str(val).strip()
            if not s:
                return []
            parts = []
            for chunk in s.replace("\n", ",").replace(";", ",").replace("|", ",").split(","):
                tag = chunk.strip()
                if tag:
                    parts.append(tag)
            return parts

        category_header = first_matching_header(
            "Category of Help",
            "Cateogry of Help",
            "Cateogry of Help (Original)",
            "Category",
        )
        if category_header:
            diag["category_header"] = category_header
            print("Category column selected:", category_header)
        else:
            print("Category column selected:", False)

        consolidated_categories = set()
        tag_columns = [f"Tag_{i:02d}" for i in range(1, 26)]
        tag_columns_found = [c for c in tag_columns if norm(c) in header_map]
        diag["tag_columns_found"] = tag_columns_found
        if tag_columns_found:
            print("Tag columns found:", tag_columns_found)
        else:
            print("Tag columns found:", False)
        tag_counts = {c: 0 for c in tag_columns_found}

        for row in ws.iter_rows(min_row=2, values_only=True):
            name = str(grab(row, "Name of Service", "Name", default="")).strip()
            address = str(grab(row, "Address", default="")).strip()
            phone = str(grab(row, "Phone Number", "Phone", default="")).strip()
            email = str(grab(row, "Email", default="")).strip()
            category = str(
                grab(
                    row,
                    "Category of Help",
                    "Cateogry of Help",
                    "Cateogry of Help (Original)",
                    "Category",
                    default="",
                )
            ).strip() or "Uncategorized"
            consolidated_value = str(
                grab(
                    row,
                    "Consolidated Category",
                    "Consolidated Tag Category",
                    default="",
                )
            ).strip()
            if consolidated_value:
                consolidated_categories.add(consolidated_value)
            taglist_header = first_matching_header("Tag_List", "Taglist", "Tag List")
            if taglist_header and diag.get("taglist_header") is None:
                diag["taglist_header"] = taglist_header
                print("Tag list column selected:", taglist_header)

            taglist_value = grab(row, "Tag_List", "Taglist", "Tag List", default="")
            tags = parse_tag_list(taglist_value)
            if not tags:
                for col in tag_columns_found:
                    val = grab(row, col, default=None)
                    if is_truthy_tag(val):
                        tags.append(col)
                        tag_counts[col] += 1
            desc = str(grab(row, "Description", default="")).strip()
            restrictions = str(grab(row, "Restrictions of Service", default="")).strip()
            days = str(grab(row, "Days of Service", default="")).strip()
            link = str(
                grab(row, "link to site", "Website", "Link", default="")
            ).strip()

            legit_raw = grab(row, "Legitimate place?", "Legitimate place ?", default="")
            confirmed_raw = grab(
                row,
                "confirmed",
                "called + confirmed?",
                "called + confirmed ?",
                default="",
            )

            reliability_raw = str(
                grab(row, "Reliability Rate 1-10", "Reliability Rate 1–10", "Reliability", default="")
            ).strip()
            avg_reliability_ratings_raw = str(
                grab(
                    row,
                    "avg_reliability_ratings",
                    "Average Reliability Ratings",
                    default="",
                )
            ).strip()
            avg_reliability_ratings = (
                avg_reliability_ratings_raw
                if avg_reliability_ratings_raw.lower() not in {"", "nan", "none"}
                else "na"
            )
            condensed_reliability_description = str(
                grab(row, "Condensed Reliability Description", default="")
            ).strip()
            reliability = (
                avg_reliability_ratings
                if avg_reliability_ratings != "na"
                else reliability_raw if reliability_raw not in {"", "nan", "none"} else "na"
            )

            call_exp = str(grab(row, "Call experience", default="")).strip()
            extra = str(grab(row, "Unnamed: 18", default="")).strip()
            call_notes = " | ".join([x for x in [call_exp, extra] if x])
            original_category = str(
                grab(
                    row,
                    "Consolidated Category",
                    "Consolidated Tag Category",
                    "Cateogry of Help (Original)",
                    "Category of Help (Original)",
                    default="",
                )
            ).strip()

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
                "original_category": original_category,
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
                "avg_reliability_ratings": avg_reliability_ratings,
                "condensed_reliability_description": condensed_reliability_description,
                "call_notes": call_notes,
                "tags": tags,
            }
            resources.append(res)

        diag["parsed_rows"] = len(resources)
        diag["consolidated_categories"] = sorted(consolidated_categories)
        diag["tag_counts"] = tag_counts
        if resources:
            diag["sample_row"] = resources[0]

    except Exception as e:
        diag["errors"].append(f"{type(e).__name__}: {e}")

    return resources, diag


def resources_map(request):
    """Main map view – loads data from Excel and passes it into the template."""
    resources, diag = _load_resources_from_xlsx()
    categories = sorted({r.get("category") for r in resources if r.get("category")})
    print("Categories passed to template:", categories)
    consolidated_categories = diag.get("consolidated_categories", [])

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
            f"Tag columns found: {diag.get('tag_columns_found')}\n"
            f"Tag counts: {diag.get('tag_counts')}\n"
            f"Errors: {diag['errors']}\n"
            f"Sample row: {diag['sample_row']}"
            .replace("\n", "<br>")
        )

    # Normal map render
    return render(
        request,
        "map_home.html",
        {"resources": resources, "consolidated_categories": consolidated_categories},
    )


def home_page(request):
    feedback_items = list(
        CommunityFeedback.objects.filter(approved=True)
        .order_by("-created_at")
        .values("title", "body")[:3]
    )
    return render(request, "home.html", {"feedback_items": feedback_items})


def resource_count(request):
    resources, _diag = _load_resources_from_xlsx()
    return JsonResponse({"count": len(resources)})


FEATURE_PAGES = {
    "mobile-first": {
        "eyebrow": "Accessibility",
        "title": "Mobile-first",
        "summary": "The site is designed to work well on phones so residents and volunteers can use it in the field, on transit, or during urgent searches.",
        "intro": (
            "Many people access community resources from a phone, not a desktop. That means the experience has to stay readable, lightweight, and easy to navigate on smaller screens."
        ),
        "highlights": [
            "Core actions are kept visible and simple so users can get to the map or guided flow quickly.",
            "Layouts are built to remain legible on smaller devices, including in lower-attention or on-the-go situations.",
            "We prioritize straightforward interactions over clutter so information stays usable when time and bandwidth are limited.",
        ],
        "commitment_title": "Why this matters",
        "commitment_body": (
            "If a resource tool only works well on a large screen, it fails many of the people who need it most. A mobile-first approach keeps access practical in real-world conditions."
        ),
        "ctas": [{"label": "Open the map", "url_name": "resources_map", "primary": False}],
    },
    "community-led": {
        "eyebrow": "Community Input",
        "title": "Open & Community-led",
        "summary": "The project improves through local feedback, corrections, and suggestions rather than pretending the first version of the dataset is enough.",
        "intro": (
            "Community resource information is never fully finished. Services change, people notice gaps, and local knowledge often reveals what a spreadsheet misses."
        ),
        "highlights": [
            "We treat suggestions and corrections as part of the maintenance process, not as an afterthought.",
            "The project is volunteer-driven, which means feedback from residents and organizers directly helps improve coverage.",
            "A community-led model makes the directory more accountable to lived experience rather than relying only on static public listings.",
        ],
        "commitment_title": "Why this matters",
        "commitment_body": (
            "A useful directory should evolve with the people who rely on it. Community feedback helps us catch omissions, improve clarity, and focus on what is actually useful on the ground."
        ),
        "ctas": [
            {"label": "Send feedback", "url_name": "community", "primary": True},
            {"label": "Open the map", "url_name": "resources_map", "primary": False},
        ],
    },
}


QUESTION_DEFAULTS = {
    "travel_access": {
        "value": "transit",
        "question": "Travel access",
        "assumed_label": "Transit, rides, or some travel",
    },
    "immediate_danger": {
        "value": "no",
        "question": "Immediate danger",
        "assumed_label": "No",
    },
    "mental_health_crisis": {
        "value": "no",
        "question": "Mental health crisis",
        "assumed_label": "No",
    },
    "unsafe_home": {
        "value": "no",
        "question": "Unsafe home",
        "assumed_label": "No",
    },
    "safe_place_tonight": {
        "value": "yes",
        "question": "Safe place to sleep tonight",
        "assumed_label": "Yes",
    },
    "food_today": {
        "value": "yes",
        "question": "Enough food for today",
        "assumed_label": "Yes",
    },
    "housing_risk": {
        "value": "no",
        "question": "Housing risk",
        "assumed_label": "No",
    },
    "utilities_help": {
        "value": "no",
        "question": "Utilities or bills help",
        "assumed_label": "No",
    },
    "transportation_needed": {
        "value": "no",
        "question": "Transportation needed",
        "assumed_label": "No",
    },
    "essential_supplies": {
        "value": "no",
        "question": "Essential supplies needed",
        "assumed_label": "No",
    },
    "employment_help": {
        "value": "no",
        "question": "Employment help",
        "assumed_label": "No",
    },
    "family_support": {
        "value": "no",
        "question": "Child or family support",
        "assumed_label": "No",
    },
    "senior_support": {
        "value": "no",
        "question": "Senior support",
        "assumed_label": "No",
    },
    "disability_support": {
        "value": "no",
        "question": "Disability or accessibility support",
        "assumed_label": "No",
    },
    "resource_navigation": {
        "value": "no",
        "question": "General resource navigation",
        "assumed_label": "No",
    },
}


def questionnaire_page(request):
    if request.method == "POST":
        def get(name):
            return (request.POST.get(name) or "").strip()

        def get_list(name):
            return [v for v in request.POST.getlist(name) if v]

        default_assumptions = []

        answers = {
            "user_lat": get("user_lat"),
            "user_lng": get("user_lng"),
            "health_support": get_list("health_support"),
            "documents_help": get_list("documents_help"),
        }
        for field_name, meta in QUESTION_DEFAULTS.items():
            raw_value = get(field_name)
            if raw_value:
                answers[field_name] = raw_value
                continue

            answers[field_name] = meta["value"]
            default_assumptions.append(
                {
                    "question": meta["question"],
                    "assumed_label": meta["assumed_label"],
                }
            )

        resources, _diag = _load_resources_from_xlsx()
        triage_result = build_triage_result(answers, resources)
        triage_result["total_recommended"] = triage_result["resource_count"]
        triage_result["default_assumptions"] = default_assumptions
        triage_result["default_assumption_count"] = len(default_assumptions)

        return render(
            request,
            "map_recommended.html",
            triage_result,
        )

    return render(request, "questionnaire.html")


def actions_page(request):
    return render(request, "actions.html")


def about_page(request):
    return render(request, "about.html")


def community_page(request):
    category_labels = dict(CommunityFeedback.CATEGORY_CHOICES)
    categories = [
        (CommunityFeedback.CATEGORY_CORRECTION, category_labels[CommunityFeedback.CATEGORY_CORRECTION]),
        (CommunityFeedback.CATEGORY_SUGGESTION, category_labels[CommunityFeedback.CATEGORY_SUGGESTION]),
        (CommunityFeedback.CATEGORY_EXPERIENCE, category_labels[CommunityFeedback.CATEGORY_EXPERIENCE]),
        (CommunityFeedback.CATEGORY_BUG, category_labels[CommunityFeedback.CATEGORY_BUG]),
    ]
    active_category = (request.GET.get("category") or "").strip()
    form_data = {
        "name": "",
        "category": CommunityFeedback.CATEGORY_SUGGESTION,
        "title": "",
        "body": "",
    }
    errors = {}

    if request.method == "POST":
        form_data = {
            "name": (request.POST.get("name") or "").strip(),
            "category": (request.POST.get("category") or "").strip(),
            "title": (request.POST.get("title") or "").strip(),
            "body": (request.POST.get("body") or "").strip(),
        }

        valid_categories = {value for value, _label in categories}

        if form_data["category"] not in valid_categories:
            errors["category"] = "Choose a valid feedback type."
        if not form_data["title"]:
            errors["title"] = "Add a short title."
        if not form_data["body"]:
            errors["body"] = "Add your feedback before submitting."

        if not errors:
            CommunityFeedback.objects.create(
                name=form_data["name"],
                category=form_data["category"],
                title=form_data["title"],
                body=form_data["body"],
                approved=True,
            )
            redirect_url = reverse("community")
            if active_category:
                redirect_url = f"{redirect_url}?submitted=1&category={active_category}"
            else:
                redirect_url = f"{redirect_url}?submitted=1"
            return redirect(redirect_url)

    valid_categories = {value for value, _label in categories}
    if active_category not in valid_categories:
        active_category = ""
    posts = CommunityFeedback.objects.all().order_by("-created_at")

    return render(
        request,
        "community.html",
        {
            "posts": posts,
            "categories": categories,
            "active_category": active_category,
            "form_data": form_data,
            "errors": errors,
            "submitted": request.GET.get("submitted") == "1",
        },
    )


def feature_detail_page(request, slug):
    feature = FEATURE_PAGES.get(slug)
    if feature is None:
        raise Http404("Feature page not found")
    return render(request, "feature_detail.html", {"feature": feature, "feature_slug": slug})


# debug endpoint still available
def ping(request):
    return HttpResponse("pong")
