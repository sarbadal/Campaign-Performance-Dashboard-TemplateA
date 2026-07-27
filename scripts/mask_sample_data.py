from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


SALT = "campaign-template-a-sample-mask-v1"

ID_COLUMNS = {"CAMPAIGN_ID", "ADSET_ID", "AD_ID"}
TEXT_COLUMNS = {
    "CAMPAIGN_NAME",
    "CAMPAIGN_GROUP",
    "ADSET_NAME",
    "AD_NAME",
    "OBJECTIVE",
    "PLATFORM",
}

STYLE_PRESETS: dict[str, dict[str, list[str]]] = {
    "retail": {
        "platform": [
            "Search Network",
            "Social Feed",
            "Video Network",
            "Display Network",
            "Discovery Network",
            "Marketplace Feed",
            "Retail Media Network",
            "Affiliate Network",
            "Shopping Grid",
            "Influencer Network",
            "In-App Display",
            "Connected TV",
        ],
        "objective": [
            "Brand Awareness",
            "Store Traffic",
            "Catalog Engagement",
            "Promo Conversion",
            "Basket Growth",
            "Loyalty Retention",
        ],
        "campaign_theme": [
            "Weekend Saver",
            "Market Fresh",
            "Value Picks",
            "Seasonal Select",
            "Smart Choice",
            "Home Essentials",
            "Family Pantry",
            "Daily Boost",
        ],
        "campaign_motion": ["Promo", "Launch", "Demand", "Retention", "Scale", "Impact"],
        "group_region": [
            "North Region",
            "Central Region",
            "South Region",
            "East Region",
            "Metro Region",
        ],
        "group_stage": [
            "Prospecting Cohort",
            "Nurture Cohort",
            "Conversion Cohort",
            "Loyalty Cohort",
        ],
        "audience_persona": [
            "Value Shoppers",
            "Family Planners",
            "Bulk Buyers",
            "Quick Refill Buyers",
            "Health Conscious Buyers",
            "Weekend Deal Hunters",
        ],
        "audience_intent": [
            "Intent Segment",
            "Interest Segment",
            "Affinity Segment",
            "Lookalike Segment",
            "Retention Segment",
        ],
        "creative_format": [
            "Promo Banner",
            "Offer Spotlight",
            "Product Reel",
            "Price Drop Cut",
            "Collection Showcase",
            "Shelf Story",
        ],
        "creative_tone": ["Bold Voice", "Warm Voice", "Direct Voice", "Friendly Voice", "Value Voice"],
    },
    "finance": {
        "platform": [
            "Search Network",
            "Professional Feed",
            "Video Network",
            "Display Network",
            "Publisher Network",
            "Finance Portal Network",
            "Advisor Media Network",
            "Programmatic Display",
            "Native Content Feed",
            "Connected TV",
            "Mobile In-App",
            "Affiliate Network",
        ],
        "objective": [
            "Account Growth",
            "Lead Qualification",
            "Application Completion",
            "Portfolio Engagement",
            "Wealth Awareness",
            "Customer Retention",
        ],
        "campaign_theme": [
            "Future Secure",
            "Capital Path",
            "Credit Smart",
            "Wealth Horizon",
            "Trust Anchor",
            "Goal Builder",
            "Prime Advantage",
            "Legacy Plan",
        ],
        "campaign_motion": ["Awareness", "Acquisition", "Onboarding", "Retention", "Expansion", "Advisory"],
        "group_region": ["North Hub", "Central Hub", "South Hub", "Coastal Hub", "Metro Hub"],
        "group_stage": ["Prospect Cohort", "Nurture Cohort", "Conversion Cohort", "Relationship Cohort"],
        "audience_persona": [
            "Emerging Investors",
            "Salary Professionals",
            "Small Business Owners",
            "Family Planners",
            "Affluent Clients",
            "Retirement Planners",
        ],
        "audience_intent": ["Intent Segment", "Affinity Segment", "Risk Profile Segment", "Lookalike Segment", "Retention Segment"],
        "creative_format": ["Advisor Story", "Plan Explainer", "Benefit Spotlight", "Rate Update", "Case Study Reel", "Portfolio Brief"],
        "creative_tone": ["Trusted Voice", "Professional Voice", "Clear Voice", "Assured Voice", "Premium Voice"],
    },
    "b2b": {
        "platform": [
            "Search Network",
            "Professional Feed",
            "Video Network",
            "Display Network",
            "Partner Network",
            "ABM Network",
            "Syndicated Content Hub",
            "Industry Publisher Network",
            "Programmatic B2B Display",
            "Webinar Promotion Network",
            "Connected TV",
            "Mobile In-App",
        ],
        "objective": [
            "Pipeline Growth",
            "Qualified Leads",
            "Demo Bookings",
            "Product Adoption",
            "Expansion Revenue",
            "Customer Success",
        ],
        "campaign_theme": [
            "Scale Engine",
            "Ops Clarity",
            "Team Velocity",
            "Data Advantage",
            "Growth Stack",
            "Workflow Shift",
            "Enterprise Edge",
            "Revenue Signal",
        ],
        "campaign_motion": ["Awareness", "Demand", "Evaluation", "Conversion", "Expansion", "Retention"],
        "group_region": ["Americas Cluster", "EMEA Cluster", "APAC Cluster", "Mid-Market Cluster", "Enterprise Cluster"],
        "group_stage": ["Prospect Cohort", "MQL Cohort", "SQL Cohort", "Customer Cohort"],
        "audience_persona": ["Ops Leaders", "Marketing Directors", "Revenue Teams", "IT Managers", "Procurement Leads", "Founders"],
        "audience_intent": ["Intent Segment", "In-Market Segment", "Lookalike Segment", "Category Segment", "Retention Segment"],
        "creative_format": ["Product Demo", "Use Case Reel", "Workflow Explainer", "ROI Snapshot", "Customer Story", "Feature Launch"],
        "creative_tone": ["Confident Voice", "Direct Voice", "Technical Voice", "Executive Voice", "Practical Voice"],
    },
}

VALID_NAMING_STYLES = set(STYLE_PRESETS)

RATE_COLUMNS = {
    "ENGAGEMENT_RATE",
    "VIDEO_PLAYS_AT_25",
    "VIDEO_PLAYS_AT_50",
    "VIDEO_PLAYS_AT_75",
    "VIDEO_PLAYS_AT_100",
}


def _stable_int(value: str) -> int:
    digest = hashlib.sha256((SALT + "|" + value).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _pick(options: list[str], seed: int, offset: int = 0) -> str:
    return options[(seed + offset) % len(options)]


def _build_semantic_label(column: str, raw_value: str, labels: dict[str, list[str]]) -> str:
    seed = _stable_int(f"label|{column}|{raw_value}")

    if column == "PLATFORM":
        return _pick(labels["platform"], seed)

    if column == "OBJECTIVE":
        return _pick(labels["objective"], seed)

    if column == "CAMPAIGN_NAME":
        theme = _pick(labels["campaign_theme"], seed)
        motion = _pick(labels["campaign_motion"], seed, 3)
        return f"{theme} {motion} Initiative"

    if column == "CAMPAIGN_GROUP":
        region = _pick(labels["group_region"], seed)
        stage = _pick(labels["group_stage"], seed, 5)
        return f"{region} {stage}"

    if column == "ADSET_NAME":
        persona = _pick(labels["audience_persona"], seed)
        intent = _pick(labels["audience_intent"], seed, 7)
        return f"{persona} {intent}"

    if column == "AD_NAME":
        creative_format = _pick(labels["creative_format"], seed)
        tone = _pick(labels["creative_tone"], seed, 11)
        return f"{creative_format} {tone}"

    return "Sample Label"


def _mapped_label(
    column: str,
    raw_value: str,
    cache: dict[str, dict[str, str]],
    labels: dict[str, list[str]],
) -> str:
    cache_for_column = cache.setdefault(column, {})
    if raw_value in cache_for_column:
        return cache_for_column[raw_value]

    label = _build_semantic_label(column, raw_value, labels)
    cache_for_column[raw_value] = label
    return label


def _platform_for_row(row_key: str, labels: dict[str, list[str]]) -> str:
    seed = _stable_int(f"platform-row|{row_key}")
    return _pick(labels["platform"], seed)


def _row_has_content(row: dict[str, str], fieldnames: list[str]) -> bool:
    for col in fieldnames:
        if str(row.get(col, "")).strip():
            return True
    return False


def _build_balanced_platform_map(
    rows: list[dict[str, str]],
    fieldnames: list[str],
    labels: dict[str, list[str]],
) -> dict[int, str]:
    platform_labels = labels["platform"]
    eligible: list[tuple[int, int]] = []

    for idx, row in enumerate(rows):
        if not _row_has_content(row, fieldnames):
            continue

        key_parts = [
            str(idx),
            row.get("DATE", ""),
            row.get("CAMPAIGN_NAME", ""),
            row.get("AD_ID", ""),
        ]
        row_key = "|".join(key_parts)
        order_seed = _stable_int(f"platform-balance|{row_key}")
        eligible.append((order_seed, idx))

    eligible.sort(key=lambda x: x[0])

    platform_map: dict[int, str] = {}
    for n, (_, row_idx) in enumerate(eligible):
        platform_map[row_idx] = platform_labels[n % len(platform_labels)]

    return platform_map


def _masked_numeric_id(column: str, raw_value: str, cache: dict[str, dict[str, str]]) -> str:
    cache_for_column = cache.setdefault(column, {})
    if raw_value in cache_for_column:
        return cache_for_column[raw_value]

    source = raw_value.strip()
    if not source:
        return ""

    target_len = max(len(source), 8)
    base_value = _stable_int(f"{column}|{source}")
    digits = str(base_value)

    while len(digits) < target_len:
        digits += str(_stable_int(digits))

    masked = digits[:target_len]
    if masked[0] == "0":
        masked = "7" + masked[1:]

    cache_for_column[raw_value] = masked
    return masked


def _value_noise(row_key: str, column: str) -> float:
    return 0.88 + (_stable_int(f"noise|{row_key}|{column}") % 2500) / 10000.0


def _column_scale(column: str) -> float:
    return 0.78 + (_stable_int(f"scale|{column}") % 4200) / 10000.0


def _format_with_original_precision(raw: str, value: float) -> str:
    token = raw.strip()
    if token == "":
        return ""

    if "." not in token:
        return str(int(round(value)))

    decimals = len(token.split(".", 1)[1])
    return f"{value:.{decimals}f}"


def _mask_numeric(raw: str, row_key: str, column: str) -> str:
    token = raw.strip()
    if token == "":
        return ""

    normalized = token.replace(",", "")
    try:
        original = float(normalized)
    except ValueError:
        return raw

    if original == 0:
        return _format_with_original_precision(token, 0.0)

    transformed = original * _column_scale(column) * _value_noise(row_key, column)

    if column in RATE_COLUMNS:
        transformed = max(0.0, min(100.0, transformed))

    if transformed < 0:
        transformed = 0.0

    return _format_with_original_precision(token, transformed)


def mask_csv(
    input_path: Path,
    output_path: Path,
    text_only: bool = False,
    naming_style: str = "retail",
    balance_platforms: bool = False,
) -> None:
    with input_path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError("CSV has no headers")

        rows = list(reader)

    text_cache: dict[str, dict[str, str]] = {}
    id_cache: dict[str, dict[str, str]] = {}
    labels = STYLE_PRESETS.get(naming_style, STYLE_PRESETS["retail"])
    balanced_platform_map = (
        _build_balanced_platform_map(rows, fieldnames, labels)
        if balance_platforms
        else {}
    )

    for idx, row in enumerate(rows):
        key_parts = [
            str(idx),
            row.get("DATE", ""),
            row.get("CAMPAIGN_NAME", ""),
            row.get("AD_ID", ""),
        ]
        row_key = "|".join(key_parts)

        for column in fieldnames:
            raw = row.get(column, "")

            if column == "PLATFORM":
                if balance_platforms and idx in balanced_platform_map:
                    row[column] = balanced_platform_map[idx]
                else:
                    row[column] = _platform_for_row(row_key, labels) if raw.strip() else ""
                continue

            if column in TEXT_COLUMNS:
                row[column] = _mapped_label(column, raw, text_cache, labels) if raw.strip() else ""
                continue

            if text_only:
                continue

            if column in ID_COLUMNS:
                row[column] = _masked_numeric_id(column, raw, id_cache)
                continue

            if column == "DATE":
                continue

            row[column] = _mask_numeric(raw, row_key, column)

    with output_path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mask campaign CSV into reusable sample data.")
    parser.add_argument("--input", default="data/data.csv", help="Input CSV path")
    parser.add_argument(
        "--output",
        default="",
        help="Output CSV path. If omitted, input file is replaced in place.",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Only remask text labels (campaign/group/audience/creative/objective/platform).",
    )
    parser.add_argument(
        "--naming-style",
        default="retail",
        choices=sorted(VALID_NAMING_STYLES),
        help="Semantic naming style for generated labels.",
    )
    parser.add_argument(
        "--balance-platforms",
        action="store_true",
        help="Distribute platform labels as evenly as possible across non-empty rows.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    mask_csv(
        input_path=input_path,
        output_path=output_path,
        text_only=args.text_only,
        naming_style=args.naming_style,
        balance_platforms=args.balance_platforms,
    )


if __name__ == "__main__":
    main()
