import math
from urllib.parse import quote


TIER_LABELS = {
    1: "Safety First",
    2: "Needs Right Now",
    3: "Prevent Things From Getting Worse",
    4: "Stabilization",
    5: "Longer-Term Support",
}


RELIABILITY_META = [
    {"label": "Highly Reliable", "color": "#22c55e"},
    {"label": "Reliable", "color": "#65a30d"},
    {"label": "Thin Reviews", "color": "#0891b2"},
    {"label": "Mixed Reviews", "color": "#f59e0b"},
    {"label": "Low Reliability", "color": "#ef4444"},
    {"label": "Not Yet Confirmed", "color": "#9ca3af"},
]


TRAVEL_PROFILES = {
    "walking": {
        "label": "Walking or very limited travel",
        "max_miles": 2.0,
        "soft_cap": 1.0,
        "distance_weight": 18,
    },
    "transit": {
        "label": "Transit, rides, or some travel",
        "max_miles": 6.0,
        "soft_cap": 3.0,
        "distance_weight": 10,
    },
    "driving": {
        "label": "Car access or broader travel",
        "max_miles": 15.0,
        "soft_cap": 7.0,
        "distance_weight": 5,
    },
    "flexible": {
        "label": "Flexible search radius",
        "max_miles": 25.0,
        "soft_cap": 10.0,
        "distance_weight": 2,
    },
}


USER_TAGS = {
    "immediate_danger": {
        "label": "Immediate Danger",
        "tier": 1,
        "kind": "crisis",
        "resource_categories": [],
        "resource_keywords": [],
    },
    "mental_health_crisis": {
        "label": "Mental Health Crisis",
        "tier": 1,
        "kind": "crisis",
        "resource_categories": ["Behavioral Health, Substance Use, & Crisis"],
        "resource_keywords": ["crisis", "hotline", "988", "mental health", "behavioral health"],
    },
    "domestic_violence_unsafe_home": {
        "label": "Domestic Violence / Unsafe Home",
        "tier": 1,
        "kind": "crisis",
        "resource_categories": ["Safety & Anti-Violence", "Housing & Shelter"],
        "resource_keywords": ["domestic violence", "dv", "sexual assault", "abuse", "safe haven"],
    },
    "no_safe_place_tonight": {
        "label": "No Safe Place Tonight",
        "tier": 2,
        "kind": "temporary",
        "resource_categories": ["Housing & Shelter"],
        "resource_keywords": ["shelter", "supportive housing", "homeless", "day center", "safe haven"],
    },
    "food_needed_today": {
        "label": "Food Needed Today",
        "tier": 2,
        "kind": "temporary",
        "resource_categories": ["Food & Essential Needs"],
        "resource_keywords": ["food", "pantry", "meal", "hot meal", "groceries"],
    },
    "medical_care_needed": {
        "label": "Medical or Mental Health Care Needed",
        "tier": 2,
        "kind": "temporary",
        "resource_categories": [
            "Physical & General Health Care",
            "Behavioral Health, Substance Use, & Crisis",
        ],
        "resource_keywords": ["medical", "health", "clinic", "hospital", "mental health", "behavioral health"],
    },
    "medication_prescription_help": {
        "label": "Medication / Prescription Help",
        "tier": 2,
        "kind": "temporary",
        "resource_categories": ["Physical & General Health Care"],
        "resource_keywords": ["prescription", "pharmacy", "medication"],
    },
    "at_risk_of_losing_housing": {
        "label": "At Risk of Losing Housing",
        "tier": 3,
        "kind": "temporary",
        "resource_categories": ["Housing & Shelter"],
        "resource_keywords": ["housing", "rent", "eviction", "tenant", "landlord", "supportive housing"],
    },
    "utilities_bills_help": {
        "label": "Utilities / Bills Help",
        "tier": 3,
        "kind": "temporary",
        "resource_categories": ["Other / Uncategorized"],
        "category_weight": 30,
        "resource_keywords": ["utility", "utilities", "energy", "ohep", "fuel fund", "water", "electric", "gas"],
    },
    "transportation_needed": {
        "label": "Transportation Needed",
        "tier": 3,
        "kind": "temporary",
        "resource_categories": [
            "Other / Uncategorized",
            "Employment, Training, & Education",
            "Physical & General Health Care",
        ],
        "category_weight": 28,
        "resource_keywords": ["transport", "transit", "bus", "paratransit", "vehicle"],
    },
    "substance_use_support": {
        "label": "Substance Use Support",
        "tier": 3,
        "kind": "temporary",
        "resource_categories": ["Behavioral Health, Substance Use, & Crisis"],
        "resource_keywords": ["substance", "recovery", "addiction", "detox", "sobriety"],
    },
    "ongoing_food_support": {
        "label": "Ongoing Food Support",
        "tier": 4,
        "kind": "temporary",
        "resource_categories": ["Food & Essential Needs"],
        "resource_keywords": ["food", "pantry", "meal", "benefits", "snap"],
    },
    "legal_id_documents": {
        "label": "Legal / ID Documents",
        "tier": 4,
        "kind": "temporary",
        "resource_categories": ["Other / Uncategorized", "Employment, Training, & Education"],
        "category_weight": 28,
        "resource_keywords": ["state id", "legal", "documents", "document", "birth certificate", "social security", "re-entry", "tenant", "landlord"],
    },
    "hygiene_clothing_supplies": {
        "label": "Hygiene / Clothing / Supplies",
        "tier": 4,
        "kind": "temporary",
        "resource_categories": ["Food & Essential Needs", "Other / Uncategorized"],
        "resource_keywords": ["hygiene", "clothing", "blanket", "basic needs", "diapers", "supplies"],
    },
    "child_family_support": {
        "label": "Child / Family Support",
        "tier": 4,
        "kind": "context",
        "resource_categories": [
            "Youth, Family, & General Support Services",
            "Food & Essential Needs",
            "Housing & Shelter",
        ],
        "resource_keywords": ["child", "children", "family", "parent", "youth", "early childhood"],
    },
    "employment_help": {
        "label": "Employment Help",
        "tier": 5,
        "kind": "context",
        "resource_categories": ["Employment, Training, & Education"],
        "resource_keywords": ["employment", "job", "career", "vocational", "training", "resume"],
    },
    "senior_support": {
        "label": "Senior Support",
        "tier": 5,
        "kind": "context",
        "resource_categories": ["Physical & General Health Care", "Other / Uncategorized"],
        "category_weight": 26,
        "resource_keywords": ["senior", "older adult", "aging", "adult day"],
    },
    "disability_accessibility_need": {
        "label": "Disability / Accessibility Need",
        "tier": 5,
        "kind": "context",
        "resource_categories": ["Physical & General Health Care", "Housing & Shelter", "Other / Uncategorized"],
        "resource_keywords": ["disability", "accessible", "accessibility", "mobility", "wheelchair"],
    },
    "language_immigration_support": {
        "label": "Language / Immigration Support",
        "tier": 5,
        "kind": "context",
        "resource_categories": ["Other / Uncategorized", "Youth, Family, & General Support Services"],
        "category_weight": 24,
        "resource_keywords": ["immigration", "language", "translation", "esol", "interpreter"],
    },
    "general_resource_navigation": {
        "label": "General Resource Navigation",
        "tier": 5,
        "kind": "context",
        "resource_categories": ["Other / Uncategorized", "Youth, Family, & General Support Services"],
        "category_weight": 26,
        "resource_keywords": ["assistance programs", "case management", "referrals", "navigation"],
    },
}


CRISIS_ACTIONS = {
    "immediate_danger": {
        "title": "Call 911 now",
        "body": "Use emergency services if you are in immediate danger, seriously injured, or cannot stay safe where you are.",
        "cta_label": "Call 911",
        "cta_href": "tel:911",
    },
    "mental_health_crisis": {
        "title": "Call or text 988 now",
        "body": "Use 988 if you may harm yourself or someone else, or if you need immediate mental health or substance-use crisis support.",
        "cta_label": "Call 988",
        "cta_href": "tel:988",
    },
    "domestic_violence_unsafe_home": {
        "title": "Prioritize immediate safety",
        "body": "If you are unsafe because of violence, threats, or coercion, use the safety resources below first. If you need emergency intervention right now, call 911.",
        "cta_label": "Call 911 if unsafe now",
        "cta_href": "tel:911",
    },
}


QUESTION_ORDER = [
    "immediate_danger",
    "mental_health_crisis",
    "domestic_violence_unsafe_home",
    "no_safe_place_tonight",
    "food_needed_today",
    "medical_care_needed",
    "medication_prescription_help",
    "at_risk_of_losing_housing",
    "utilities_bills_help",
    "transportation_needed",
    "substance_use_support",
    "ongoing_food_support",
    "legal_id_documents",
    "hygiene_clothing_supplies",
    "child_family_support",
    "employment_help",
    "senior_support",
    "disability_accessibility_need",
    "language_immigration_support",
    "general_resource_navigation",
]


def ordered_tag_keys(tag_keys):
    order_map = {key: idx for idx, key in enumerate(QUESTION_ORDER)}
    return sorted(
        tag_keys,
        key=lambda key: (USER_TAGS[key]["tier"], order_map.get(key, 999)),
    )


def build_tag_payload(tag_key):
    meta = USER_TAGS[tag_key]
    return {
        "key": tag_key,
        "label": meta["label"],
        "tier": meta["tier"],
        "tier_label": TIER_LABELS[meta["tier"]],
        "kind": meta["kind"],
    }


def _parse_float(value):
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _miles_between(lat1, lng1, lat2, lng2):
    lat1 = _parse_float(lat1)
    lng1 = _parse_float(lng1)
    lat2 = _parse_float(lat2)
    lng2 = _parse_float(lng2)
    if None in {lat1, lng1, lat2, lng2}:
        return None

    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_miles * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def derive_user_tags(answers):
    tags = set()

    if answers.get("immediate_danger") == "yes":
        tags.add("immediate_danger")
    if answers.get("mental_health_crisis") == "yes":
        tags.add("mental_health_crisis")
    if answers.get("unsafe_home") == "yes":
        tags.add("domestic_violence_unsafe_home")

    safe_place = answers.get("safe_place_tonight")
    if safe_place == "no":
        tags.add("no_safe_place_tonight")
    elif safe_place == "at_risk":
        tags.add("at_risk_of_losing_housing")

    food_today = answers.get("food_today")
    if food_today == "no":
        tags.add("food_needed_today")
    elif food_today == "ongoing":
        tags.add("ongoing_food_support")

    health_support = set(answers.get("health_support", []))
    if {"medical_care", "mental_health_support"} & health_support:
        tags.add("medical_care_needed")
    if "prescription_help" in health_support:
        tags.add("medication_prescription_help")
    if "substance_use_support" in health_support:
        tags.add("substance_use_support")

    if answers.get("housing_risk") == "yes":
        tags.add("at_risk_of_losing_housing")
    if answers.get("utilities_help") == "yes":
        tags.add("utilities_bills_help")
    if answers.get("transportation_needed") == "yes":
        tags.add("transportation_needed")
    if answers.get("essential_supplies") == "yes":
        tags.add("hygiene_clothing_supplies")

    documents_help = set(answers.get("documents_help", []))
    if "legal_id" in documents_help:
        tags.add("legal_id_documents")
    if "immigration_language" in documents_help:
        tags.add("language_immigration_support")

    if answers.get("employment_help") == "yes":
        tags.add("employment_help")
    if answers.get("family_support") == "yes":
        tags.add("child_family_support")
    if answers.get("senior_support") == "yes":
        tags.add("senior_support")
    if answers.get("disability_support") == "yes":
        tags.add("disability_accessibility_need")
    if answers.get("resource_navigation") == "yes" or not tags:
        tags.add("general_resource_navigation")

    ordered = ordered_tag_keys(tags)
    payloads = [build_tag_payload(key) for key in ordered]
    grouped = {}
    for payload in payloads:
        grouped.setdefault(payload["tier"], []).append(payload)

    priority_groups = [
        {
            "tier": tier,
            "label": TIER_LABELS[tier],
            "tags": grouped[tier],
        }
        for tier in sorted(grouped)
    ]

    return {
        "active_keys": ordered,
        "active_tags": payloads,
        "priority_groups": priority_groups,
        "crisis_tags": [payload for payload in payloads if payload["kind"] == "crisis"],
        "temporary_tags": [payload for payload in payloads if payload["kind"] == "temporary"],
        "context_tags": [payload for payload in payloads if payload["kind"] == "context"],
    }


def build_search_profile(answers, active_keys):
    travel_mode = answers.get("travel_access") or "transit"
    base_profile = dict(TRAVEL_PROFILES.get(travel_mode, TRAVEL_PROFILES["transit"]))
    highest_priority = min((USER_TAGS[key]["tier"] for key in active_keys), default=5)
    user_lat = _parse_float(answers.get("user_lat"))
    user_lng = _parse_float(answers.get("user_lng"))

    if "transportation_needed" in active_keys:
        base_profile["max_miles"] = max(1.5, round(base_profile["max_miles"] * 0.7, 1))
        base_profile["soft_cap"] = max(0.8, round(base_profile["soft_cap"] * 0.7, 1))
        base_profile["distance_weight"] += 6

    if highest_priority <= 2:
        base_profile["max_miles"] = max(2.0, round(base_profile["max_miles"] * 0.85, 1))
        base_profile["soft_cap"] = max(1.0, round(base_profile["soft_cap"] * 0.85, 1))

    base_profile.update(
        {
            "travel_mode": travel_mode,
            "highest_priority": highest_priority,
            "user_lat": user_lat,
            "user_lng": user_lng,
            "has_location": user_lat is not None and user_lng is not None,
            "expanded_search": False,
        }
    )
    return base_profile


def _resource_search_text(resource):
    parts = [
        resource.get("name", ""),
        resource.get("category", ""),
        resource.get("original_category", ""),
        resource.get("description", ""),
        resource.get("restrictions", ""),
        resource.get("days", ""),
        " ".join(resource.get("tags") or []),
    ]
    return " | ".join(str(part or "") for part in parts).lower()


def _parse_reliability(resource):
    for key in ("avg_reliability_ratings", "reliability"):
        raw = str(resource.get(key, "") or "").strip().lower()
        try:
            return float(raw)
        except Exception:
            continue
    return None


def get_reliability_meta(resource):
    rating = _parse_reliability(resource)
    if rating is None:
        return RELIABILITY_META[5]
    if rating >= 8:
        return RELIABILITY_META[0]
    if rating >= 7:
        return RELIABILITY_META[1]
    if rating >= 6:
        return RELIABILITY_META[2]
    if rating >= 4:
        return RELIABILITY_META[3]
    return RELIABILITY_META[4]


def _availability_bonus(resource):
    text = f"{resource.get('days', '')} {resource.get('restrictions', '')}".lower()
    if any(token in text for token in ["24/7", "24 hours", "24 hours/day"]):
        return 24
    if any(token in text for token in ["daily", "same day", "walk-in", "today"]):
        return 12
    return 0


def _reliability_penalty(resource, tier):
    rating = _parse_reliability(resource)
    if rating is None:
        return -8 if tier <= 3 else -4
    if tier <= 2 and rating < 4:
        return -55
    if tier <= 3 and rating < 4:
        return -35
    if rating < 5:
        return -18
    if rating < 6:
        return -8
    return 0


def _warning_note(resource, tier):
    rating = _parse_reliability(resource)
    if rating is None:
        return "Reliability has not been confirmed yet."
    if tier <= 2 and rating < 4:
        return "Use caution: this option may be less dependable for urgent needs."
    if rating < 5:
        return "Use caution: this option has mixed or lower reliability signals."
    return ""


def _availability_warning(resource, highest_priority):
    if highest_priority > 2:
        return ""
    text = f"{resource.get('days', '')} {resource.get('restrictions', '')}".lower()
    if any(token in text for token in ["24/7", "24 hours", "daily", "same day", "walk-in", "today"]):
        return ""
    return "Hours may require extra verification before you travel."


def _distance_detail(resource, search_profile, relaxed=False):
    if not search_profile.get("has_location"):
        return {
            "distance_miles": None,
            "distance_label": "",
            "score_delta": 0,
            "filtered_out": False,
        }

    distance = _miles_between(
        search_profile.get("user_lat"),
        search_profile.get("user_lng"),
        resource.get("lat"),
        resource.get("lng"),
    )
    if distance is None:
        return {
            "distance_miles": None,
            "distance_label": "",
            "score_delta": -6,
            "filtered_out": False,
        }

    max_miles = search_profile["max_miles"]
    soft_cap = search_profile["soft_cap"]
    highest_priority = search_profile["highest_priority"]
    score_delta = 0
    filtered_out = False

    if distance <= soft_cap:
        score_delta += max(0, int((soft_cap - distance) * 4))
    else:
        score_delta -= int((distance - soft_cap) * search_profile["distance_weight"])

    if highest_priority <= 3 and distance > max_miles and not relaxed:
        filtered_out = True
    elif distance > (max_miles * (2.0 if relaxed else 1.6)):
        filtered_out = True

    return {
        "distance_miles": round(distance, 1),
        "distance_label": f"{distance:.1f} mi away",
        "score_delta": score_delta,
        "filtered_out": filtered_out,
    }


def _blocked_for_urgent_reliability(resource, highest_priority, relaxed=False):
    if highest_priority > 2 or relaxed:
        return False
    rating = _parse_reliability(resource)
    return rating is not None and rating < 4


def score_resource_for_tag(resource, tag_key):
    meta = USER_TAGS[tag_key]
    text = _resource_search_text(resource)
    score = 0
    reasons = []

    category = resource.get("category") or ""
    if category in meta["resource_categories"]:
        score += meta.get("category_weight", 74)
        reasons.append(category)

    resource_tags = {str(tag).strip().lower() for tag in (resource.get("tags") or []) if str(tag).strip()}
    if tag_key in resource_tags:
        score += 110
        reasons.append("resource tag")

    keyword_hits = [keyword for keyword in meta["resource_keywords"] if keyword in text]
    if keyword_hits:
        score += min(42, 14 * len(keyword_hits))
        reasons.append(keyword_hits[0])

    if score == 0:
        return None

    score += 150 - (meta["tier"] * 18)
    if meta["tier"] <= 2:
        score += _availability_bonus(resource)
    score += _reliability_penalty(resource, meta["tier"])

    return {
        "score": score,
        "reasons": reasons,
        "warning": _warning_note(resource, meta["tier"]),
    }


def _decorate_resource(resource, match_details, total_score, search_profile, distance_detail):
    ordered_matches = sorted(
        match_details.items(),
        key=lambda item: (item[1]["score"], -USER_TAGS[item[0]]["tier"]),
        reverse=True,
    )
    reliability_meta = get_reliability_meta(resource)
    matched_tag_payloads = [build_tag_payload(tag_key) for tag_key, _detail in ordered_matches]
    first_warning = next((detail["warning"] for _tag, detail in ordered_matches if detail["warning"]), "")
    if not first_warning:
        first_warning = _availability_warning(resource, search_profile["highest_priority"])
    destination = quote(resource.get("address") or f"{resource.get('lat')},{resource.get('lng')}")

    decorated = dict(resource)
    decorated.update(
        {
            "score": total_score,
            "matched_tags": matched_tag_payloads,
            "primary_tag": matched_tag_payloads[0] if matched_tag_payloads else None,
            "reliability_meta": reliability_meta,
            "warning_note": first_warning,
            "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={destination}",
            "distance_miles": distance_detail["distance_miles"],
            "distance_label": distance_detail["distance_label"],
        }
    )
    return decorated


def _rank_resources(resources, active_keys, search_profile, relaxed=False):
    scored_resources = []

    for resource in resources:
        if _blocked_for_urgent_reliability(resource, search_profile["highest_priority"], relaxed=relaxed):
            continue

        match_details = {}
        total_score = 0
        for tag_key in active_keys:
            detail = score_resource_for_tag(resource, tag_key)
            if detail:
                match_details[tag_key] = detail
                total_score += detail["score"]

        if not match_details:
            continue

        distance_detail = _distance_detail(resource, search_profile, relaxed=relaxed)
        if distance_detail["filtered_out"]:
            continue

        total_score += distance_detail["score_delta"]
        decorated = _decorate_resource(
            resource,
            match_details,
            total_score,
            search_profile,
            distance_detail,
        )
        scored_resources.append(
            (
                min(USER_TAGS[tag_key]["tier"] for tag_key in match_details),
                -total_score,
                decorated.get("distance_miles") if decorated.get("distance_miles") is not None else 9999,
                decorated.get("name", ""),
                decorated,
            )
        )

    scored_resources.sort(key=lambda item: item[:4])
    return [item[4] for item in scored_resources]


def _group_resources_by_priority(resources):
    grouped = {}
    for resource in resources:
        tier = (resource.get("primary_tag") or {}).get("tier", 5)
        grouped.setdefault(tier, []).append(resource)

    return [
        {
            "tier": tier,
            "label": TIER_LABELS[tier],
            "resources": grouped[tier],
            "count": len(grouped[tier]),
        }
        for tier in sorted(grouped)
    ]


def _build_display_groups(tag_bundle, ranked_resources):
    display_groups = []
    for group in tag_bundle["priority_groups"]:
        tier_resources = [
            resource
            for resource in ranked_resources
            if any(tag.get("tier") == group["tier"] for tag in (resource.get("matched_tags") or []))
        ]
        display_groups.append(
            {
                "tier": group["tier"],
                "label": group["label"],
                "tags": group["tags"],
                "resources": tier_resources[:8],
                "count": len(tier_resources),
            }
        )

    return display_groups


def build_triage_result(answers, resources):
    tag_bundle = derive_user_tags(answers)
    active_keys = tag_bundle["active_keys"]
    search_profile = build_search_profile(answers, active_keys)

    ranked_resources = _rank_resources(resources, active_keys, search_profile, relaxed=False)
    if search_profile["has_location"] and len(ranked_resources) < 4:
        search_profile["expanded_search"] = True
        ranked_resources = _rank_resources(resources, active_keys, search_profile, relaxed=True)

    crisis_actions = [CRISIS_ACTIONS[tag_key] for tag_key in active_keys if tag_key in CRISIS_ACTIONS]
    resource_groups = _group_resources_by_priority(ranked_resources[:18])
    display_groups = _build_display_groups(tag_bundle, ranked_resources)

    return {
        "triage": tag_bundle,
        "crisis_actions": crisis_actions,
        "resources": ranked_resources,
        "resource_count": len(ranked_resources),
        "top_resources": ranked_resources[:12],
        "resource_groups": resource_groups,
        "display_groups": display_groups,
        "search_profile": search_profile,
    }
