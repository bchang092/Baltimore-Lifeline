#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Process an Excel file:
1) Geocode addresses into Latitude/Longitude (optional).
2) Recategorize 'Category of Help' into broader categories (optional).

Requirements:
    pip install pandas geopy openpyxl tqdm pyarrow   # or fastparquet instead of pyarrow
"""

import re
from pathlib import Path

import pandas as pd
from tqdm import tqdm  # ✅ Progress bar

# ------------- Config -------------
INPUT_PATH = Path("1109 Upload.xlsx")
SHEET_NAME = "Sheet1"

ADDRESS_COL = "Address"              # Column with addresses to geocode
CATEGORY_COL = "Cateogry of Help"    # Column to be recategorized

OUTPUT_PATH = INPUT_PATH.with_name(INPUT_PATH.stem + "_geocoded.xlsx")
CACHE_PATH = INPUT_PATH.with_name(INPUT_PATH.stem + "_geocache.parquet")

# Switches to turn processing on/off
RUN_GEOCODING = True
RUN_RECAT = True

# Geocoding provider
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter


# ----------------- Geocoding ----------------- #

def norm_addr(s):
    """Normalize address string."""
    if pd.isna(s):
        return ""
    return re.sub(r"\s+", " ", str(s).strip())


def geocode_addresses(df: pd.DataFrame) -> pd.DataFrame:
    """Geocode the ADDRESS_COL in df, filling Latitude/Longitude with caching and a progress bar."""
    if ADDRESS_COL not in df.columns:
        raise ValueError(f"Could not find the column '{ADDRESS_COL}' in the Excel file.")

    # Prepare output columns
    df["Latitude"] = df.get("Latitude", pd.NA)
    df["Longitude"] = df.get("Longitude", pd.NA)

    # Load cache if available
    if CACHE_PATH.exists():
        try:
            cache = pd.read_parquet(CACHE_PATH)
        except Exception:
            cache = pd.DataFrame(columns=["query", "lat", "lng"])
    else:
        cache = pd.DataFrame(columns=["query", "lat", "lng"])

    cache_map = dict(zip(cache["query"], cache[["lat", "lng"]].to_records(index=False)))

    # Init geocoder
    geolocator = Nominatim(user_agent="chatgpt_geocode_script", timeout=10)
    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=1.2,
        max_retries=3,
        swallow_exceptions=True,
    )

    updated = 0

    # ✅ Wrap loop in tqdm progress bar
    for idx, row in tqdm(
        df.iterrows(),
        total=len(df),
        desc="Geocoding",
        ncols=100,
    ):
        addr_raw = row[ADDRESS_COL]
        addr = norm_addr(addr_raw)
        if not addr:
            continue

        # Skip if already filled
        if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
            continue

        # Check cache
        if addr in cache_map:
            lat, lng = cache_map[addr]
            df.at[idx, "Latitude"] = lat
            df.at[idx, "Longitude"] = lng
            continue

        # Live geocode
        loc = geocode(addr)
        if loc:
            lat, lng = loc.latitude, loc.longitude
            df.at[idx, "Latitude"] = lat
            df.at[idx, "Longitude"] = lng
            cache_map[addr] = (lat, lng)
            updated += 1

    # Save cache
    cache_df = pd.DataFrame(
        [(k, v[0], v[1]) for k, v in cache_map.items()],
        columns=["query", "lat", "lng"],
    )
    try:
        cache_df.to_parquet(CACHE_PATH, index=False)
    except Exception:
        cache_df.to_csv(CACHE_PATH.with_suffix(".csv"), index=False)

    print(f"✅ Geocoding complete. Updated {updated} rows.")
    return df


# ----------------- Recategorizing ----------------- #

def classify_category(text: str) -> str:
    """
    Heuristic / keyword-based classifier that maps a raw 'Category of Help'
    string into one of 10 broad categories:

    1. Food & Essential Needs
    2. Housing & Shelter
    3. Physical & General Health Care
    4. Behavioral Health, Substance Use, & Crisis
    5. Financial & Access Support
    6. Employment, Training, & Education
    7. Youth, Family, & General Support Services
    8. Safety & Anti-Violence
    9. Veteran Services
    10. Other / Uncategorized
    """
    if pd.isna(text):
        return "Other / Uncategorized"

    s = str(text).strip().lower()

    # --- 9. Veteran Services (highest priority) ---
    if any(k in s for k in ["veteran", "va health", "va clinic"]):
        return "Veteran Services"

    # --- 8. Safety & Anti-Violence ---
    if any(k in s for k in [
        "domestic violence", "dv", "sexual assault", "intimate partner",
        "safe house", "violence", "trafficking"
    ]):
        return "Safety & Anti-Violence"

    # --- 4. Behavioral Health, Substance Use, & Crisis ---
    if any(k in s for k in [
        "behavioral health", "mental health", "psychiat", "counseling",
        "crisis", "hotline", "suicide", "harm reduction", "overdose",
        "substance use", "addiction", "recovery", "mat program", "peer support"
    ]):
        return "Behavioral Health, Substance Use, & Crisis"

    # --- 3. Physical & General Health Care ---
    if any(k in s for k in [
        "healthcare", "health care", "health center", "clinic", "medical",
        "hospital", "fqh", "fqhc", "sliding scale", "charity care",
        "vision", "dental", "women/lgbtq", "lgbtq+ health"
    ]):
        return "Physical & General Health Care"

    # --- 2. Housing & Shelter ---
    if any(k in s for k in [
        "shelter", "housing", "supportive housing", "emergency shelter",
        "transitional", "safe haven", "overnight", "rapid rehousing",
        "tenant", "landlord", "homeownership", "home repair"
    ]):
        return "Housing & Shelter"

    # --- 1. Food & Essential Needs ---
    if any(k in s for k in [
        "food", "pantry", "soup kitchen", "meal", "meals",
        "groceries", "grocery", "clothing", "clothes",
        "basic needs", "essentials", "household goods",
        "day center", "day resource"
    ]):
        return "Food & Essential Needs"

    # --- 5. Financial & Access Support ---
    if any(k in s for k in [
        "benefits", "assistance program", "financial assistance",
        "cash", "income support", "tax credit", "tax help",
        "utility assistance", "utilities", "electric", "gas bill",
        "water bill", "communications discount", "lifeline",
        "digital access", "internet", "broadband"
    ]):
        return "Financial & Access Support"

    # --- 6. Employment, Training, & Education ---
    if any(k in s for k in [
        "employment", "job", "jobs", "career", "workforce",
        "training", "job training", "vocational", "rehabilitation",
        "apprentice", "internship", "resume", "interview skills",
        "youth employment", "summer jobs", "education/employment",
        "ged", "adult education"
    ]):
        return "Employment, Training, & Education"

    # --- 7. Youth, Family, & General Support Services ---
    if any(k in s for k in [
        "youth", "teen", "family", "child", "children",
        "early childhood", "family support", "parenting",
        "mentor", "drop-in", "advocacy",
        "community space", "community center",
        "culture & food access", "community services"
    ]):
        return "Youth, Family, & General Support Services"

    # Fallback
    return "Other / Uncategorized"


def recategorize_categories(df: pd.DataFrame) -> pd.DataFrame:
    """Recategorize CATEGORY_COL into broad categories with a progress bar."""
    if CATEGORY_COL not in df.columns:
        print(f"⚠️ Column '{CATEGORY_COL}' not found. Skipping recategorization.")
        return df

    # Backup original column
    backup_col = CATEGORY_COL + " (Original)"
    if backup_col not in df.columns:
        df[backup_col] = df[CATEGORY_COL]

    tqdm.pandas(desc="Recategorizing")

    df[CATEGORY_COL] = df[CATEGORY_COL].progress_apply(classify_category)

    print("✅ Recategorization complete. Each row now has one of 10 categories.")
    return df


# ----------------- Main ----------------- #

def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Input not found: {INPUT_PATH}")

    df = pd.read_excel(INPUT_PATH, sheet_name=SHEET_NAME)

    # 1) Geocoding (optional)
    if RUN_GEOCODING:
        df = geocode_addresses(df)
    else:
        print("⏭️ Skipping geocoding (RUN_GEOCODING=False).")

    # 2) Recategorizing (optional)
    if RUN_RECAT:
        df = recategorize_categories(df)
    else:
        print("⏭️ Skipping recategorization (RUN_RECAT=False).")

    # Save output
    df.to_excel(OUTPUT_PATH, index=False)
    print(f"\n✅ Done. Wrote processed file to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
