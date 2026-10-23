#!/usr/bin/env python3
"""Build compact website analytics from local notebook CSVs.

The generated directory contains organization records and aggregate people
counts, a focused organization shortlist, and a 250-row ranked people preview.
Run from any directory with: python3 web/scripts/build_site_data.py
"""

from __future__ import annotations

import csv
import json
import math
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "web/src/data"
ORG_FILE = ROOT / "organizations_clustered.csv"
PEOPLE_FILE = ROOT / "individuals_clustered.csv"
RANKED_FILE = ROOT / "csaf_ranked_donor_prospects.csv"
MASTER_PEOPLE_FILE = ROOT / "individuals_master.csv"
MASTER_ORG_FILE = ROOT / "organizations_master.csv"
IRS_FILE = ROOT / "irs_latest_donors.csv"
CONTACT_FILE = ROOT / "contact_enrichment/output/contact_discovery.csv"
HANDOFF_FILE = ROOT / "contact_enrichment/output/csaf_email_handoff.csv"

TIERS = [
    "Tier 1 — Platinum: Disclosed Capacity, Established",
    "Tier 2 — Gold: Disclosed Capacity, Developing",
    "Tier 3 — Silver: Revenue Unreported, Repeat Filings",
    "Tier 4 — Grassroots: Revenue Unreported, Limited Signal",
]


def number(value: str | None, default: float = 0.0) -> float:
    try:
        result = float(value) if value not in (None, "") else default
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def truth(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")


def read_public_contacts() -> tuple[dict[str, list[dict]], list[dict]]:
    """Load unique, source-linked email addresses grouped by organization EIN."""
    by_ein: dict[str, list[dict]] = defaultdict(list)
    if not CONTACT_FILE.exists():
        return by_ein, []
    seen: set[tuple[str, str]] = set()
    with CONTACT_FILE.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            ein = (row.get("ein") or "").strip().replace("-", "").zfill(9)
            email = (row.get("email_address") or "").strip().lower()
            status = (row.get("status") or "").strip()
            if not ein or not email or "@" not in email or status != "published_on_official_site_not_mailbox_verified":
                continue
            key = (ein, email)
            if key in seen:
                continue
            seen.add(key)
            contact = {
                "email": email,
                "type": (row.get("contact_type") or "published site address").strip(),
                "matchedName": (row.get("matched_prospect_name") or "").strip(),
                "website": (row.get("official_website") or "").strip(),
                "phone": (row.get("organization_phone") or "").strip(),
                "evidenceUrl": (row.get("evidence_url") or "").strip(),
                "retrievedOn": (row.get("retrieved_on") or "").strip(),
                "status": status,
            }
            by_ein[ein].append(contact)
    for contacts in by_ein.values():
        contacts.sort(key=lambda item: (item["type"] != "matched prospect person", item["email"]))
    return by_ein, [contact | {"ein": ein} for ein, contacts in by_ein.items() for contact in contacts]


def write_email_handoff(contacts: list[dict], ranked_by_ein: dict[str, dict], org_by_ein: dict[str, dict]) -> list[dict]:
    """Write one auditable row per published email, keeping all contacts for review."""
    columns = [
        "organization_best_rank", "ein", "organization_name", "city", "state", "ntee_code",
        "total_revenue", "tax_period_count", "tier_name", "organization_score", "contact_name",
        "contact_type", "email_address", "official_website", "organization_phone", "evidence_url",
        "retrieved_on", "email_status",
    ]
    HANDOFF_FILE.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for contact in sorted(contacts, key=lambda item: (
        number(ranked_by_ein.get(item["ein"], {}).get("outreach_rank"), 999999),
        org_by_ein.get(item["ein"], {}).get("organization_name", "").casefold(),
        item["type"], item["email"],
    )):
        ein = contact["ein"]
        ranked = ranked_by_ein.get(ein, {})
        org = org_by_ein.get(ein, {})
        rows.append({
            "organization_best_rank": ranked.get("outreach_rank", ""),
            "ein": ein,
            "organization_name": org.get("organization_name") or ranked.get("organization_name", ""),
            "city": org.get("city") or ranked.get("city", ""),
            "state": org.get("state") or ranked.get("state", ""),
            "ntee_code": org.get("ntee_code") or ranked.get("ntee_code", ""),
            "total_revenue": org.get("total_revenue") or ranked.get("total_revenue", ""),
            "tax_period_count": org.get("tax_period_count") or ranked.get("tax_period_count", ""),
            "tier_name": ranked.get("tier_name", ""),
            "organization_score": ranked.get("outreach_priority_score", ""),
            "contact_name": contact["matchedName"],
            "contact_type": contact["type"],
            "email_address": contact["email"],
            "official_website": contact.get("website", ""),
            "organization_phone": contact.get("phone", ""),
            "evidence_url": contact["evidenceUrl"],
            "retrieved_on": contact["retrievedOn"],
            "email_status": contact["status"],
        })
    with HANDOFF_FILE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def main() -> None:
    for path in (ORG_FILE, PEOPLE_FILE, RANKED_FILE, MASTER_PEOPLE_FILE, MASTER_ORG_FILE, IRS_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Missing pipeline artifact: {path}")

    contacts_by_ein, all_contacts = read_public_contacts()

    orgs: list[dict] = []
    positive_revenues: list[float] = []
    cluster_stats: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "missing": 0, "log_revenue": [], "periods": [], "arts": 0, "market": 0, "revenue": [],
    })
    states: Counter[str] = Counter()
    macro: Counter[str] = Counter()
    missing = Counter()
    revenue_values: list[float] = []

    with ORG_FILE.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        org_columns = reader.fieldnames or []
        for row in reader:
            ein = (row.get("ein") or "").strip().zfill(9)
            revenue_raw = row.get("total_revenue", "")
            revenue = number(revenue_raw, float("nan"))
            revenue_known = math.isfinite(revenue)
            revenue_positive = max(0.0, revenue) if revenue_known else 0.0
            period_count = max(1.0, number(row.get("tax_period_count"), 1.0))
            cluster = str(row.get("cluster_id") or "")
            ntee_code = (row.get("ntee_code") or "").strip().upper()
            ntee = (row.get("ntee_macro_category") or "").strip().upper()
            if ntee in {"", "UNKNOWN", "NAN", "NONE"}:
                ntee = ntee_code[:1] if ntee_code else ""
            if ntee_code in {"UNKNOWN", "NAN", "NONE"}:
                ntee_code = ""
            city = (row.get("city") or "").strip().upper()
            state = (row.get("state") or "").strip().upper()
            nyc = truth(row.get("is_nyc_city"))
            la = truth(row.get("is_la_city"))
            arts = ntee == "A"
            stat = cluster_stats[cluster]
            stat["count"] += 1
            stat["missing"] += int(not revenue_known)
            stat["log_revenue"].append(math.log10(1 + revenue_positive))
            stat["periods"].append(period_count)
            stat["arts"] += int(arts)
            stat["market"] += int(nyc or la)
            states[state or "Unknown"] += 1
            macro[ntee or "Unknown"] += 1
            missing["revenue"] += int(not revenue_known)
            missing["ntee"] += int(not ntee)
            if revenue_known:
                revenue_values.append(revenue_positive)
                stat["revenue"].append(revenue_positive)
                if revenue_positive > 0:
                    positive_revenues.append(revenue_positive)
            orgs.append({
                "ein": ein,
                "name": row.get("organization_name") or "Organization name unavailable",
                "city": row.get("city") or "",
                "state": state,
                "ntee": ntee_code,
                "macro": ntee,
                "revenue": revenue_positive if revenue_known else None,
                "periods": int(round(period_count)),
                "cluster": cluster,
                "nyc": nyc,
                "la": la,
            })

    if not orgs:
        raise ValueError("Organization artifact contained no records")

    def median(values: list[float]) -> float:
        values = sorted(values)
        if not values:
            return 0.0
        middle = len(values) // 2
        return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2

    disclosed = [key for key, stat in cluster_stats.items() if stat["missing"] / stat["count"] < 0.5]
    undisclosed = [key for key, stat in cluster_stats.items() if stat["missing"] / stat["count"] >= 0.5]
    disclosed.sort(key=lambda key: (median(cluster_stats[key]["log_revenue"]), median(cluster_stats[key]["periods"])), reverse=True)
    undisclosed.sort(key=lambda key: (median(cluster_stats[key]["periods"]), -cluster_stats[key]["missing"] / cluster_stats[key]["count"], cluster_stats[key]["arts"] / cluster_stats[key]["count"]), reverse=True)
    ordered_clusters = disclosed + undisclosed
    if len(disclosed) != 2 or len(undisclosed) != 2:
        ordered_clusters = sorted(cluster_stats, key=lambda key: (-cluster_stats[key]["missing"] / cluster_stats[key]["count"], -median(cluster_stats[key]["periods"]), -median(cluster_stats[key]["log_revenue"])))
    cluster_tier = dict(zip(ordered_clusters, TIERS))

    positive_revenues.sort()
    cutoff = positive_revenues[math.floor(0.75 * (len(positive_revenues) - 1))] if positive_revenues else 0
    periods_all = [item["periods"] for item in orgs]
    min_periods, max_periods = min(periods_all), max(periods_all)
    for row in orgs:
        row["tier"] = cluster_tier.get(row["cluster"], "Unmapped profile")
        high_capacity = row["revenue"] is not None and row["revenue"] >= cutoff
        row["highCapacity"] = high_capacity
        row["arts"] = row["macro"] == "A"
        row["score"] = round(
            (20 if row["nyc"] or row["la"] else 0)
            + (30 if row["arts"] else 0)
            + ((bisect_right(positive_revenues, row["revenue"]) / len(positive_revenues) * 30) if row["revenue"] is not None and positive_revenues else 0)
            + ((row["periods"] - min_periods) / (max_periods - min_periods) * 20 if max_periods > min_periods else 0), 1
        )

    # Use Cell 7's saved person export to count distinct linked affiliations and
    # know which eligible organizations have at least one listed person.
    target_eins: set[str] = set()
    ranked_org_metrics: dict[str, tuple[str, float]] = {}
    target_affiliations = 0
    city_affiliations = Counter()
    people_preview: list[dict] = []
    ranked_by_ein: dict[str, dict] = {}
    with RANKED_FILE.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            target_affiliations += 1
            ein = (row.get("ein") or "").strip().zfill(9)
            target_eins.add(ein)
            ranked_org_metrics[ein] = (
                row.get("tier_name") or "Unmapped profile",
                number(row.get("outreach_priority_score")),
            )
            if ein not in ranked_by_ein or number(row.get("outreach_rank"), 999999) < number(ranked_by_ein[ein].get("outreach_rank"), 999999):
                ranked_by_ein[ein] = row
            city = (row.get("city") or "").strip().upper()
            city_affiliations["NYC" if city not in {"LOS ANGELES", "LOS ANGELES CITY"} else "Los Angeles"] += 1
            person_name_key = (row.get("human_name") or "").strip().casefold()
            matched_contact = any(
                contact["type"] == "matched prospect person"
                and contact["matchedName"].strip().casefold() == person_name_key
                for contact in contacts_by_ein.get(ein, [])
            )
            if len(people_preview) < 250 or matched_contact:
                person_revenue = number(row.get("total_revenue"), float("nan"))
                try:
                    explanations = json.loads(row.get("score_explanations") or "[]")
                except json.JSONDecodeError:
                    explanations = []
                people_preview.append({
                    "rank": int(number(row.get("outreach_rank"))),
                    "name": row.get("human_name") or "",
                    "ein": ein,
                    "organization": row.get("organization_name") or "",
                    "city": row.get("city") or "",
                    "state": row.get("state") or "",
                    "tier": row.get("tier_name") or "",
                    "score": number(row.get("outreach_priority_score")),
                    "revenue": person_revenue if math.isfinite(person_revenue) else None,
                    "periods": int(number(row.get("tax_period_count"))),
                    "ntee": row.get("ntee_code") or "",
                    "explanations": explanations,
                    "contacts": contacts_by_ein.get(ein, []),
                })
    # The organization review pool also includes eligible organizations without
    # a linked person in the ranked export. This keeps the organization view
    # complete while preserving Cell 7's reported person-affiliation totals.
    target_orgs = [row for row in orgs if (row["nyc"] or row["la"]) and (row["arts"] or row["highCapacity"])]
    for row in target_orgs:
        if row["ein"] in ranked_org_metrics:
            row["tier"], row["score"] = ranked_org_metrics[row["ein"]]

    # Basic row and missing-field counts across each notebook CSV.
    artifact_stats = {}
    for label, path in {
        "Organization master": MASTER_ORG_FILE,
        "Organization clusters": ORG_FILE,
        "Individual master": MASTER_PEOPLE_FILE,
        "Individual clusters": PEOPLE_FILE,
        "Ranked notebook export": RANKED_FILE,
        "Initial parsed filings": IRS_FILE,
    }.items():
        rows = 0
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            for _ in reader:
                rows += 1
        artifact_stats[label] = {"rows": rows, "columns": len(columns), "file": path.name}

    # Only organization identities are included in the public Vercel bundle.
    # Keep the focused review pool manageable and disclose its filtering rule.
    target_orgs.sort(key=lambda row: (-row["score"], -row["periods"], row["name"].casefold()))
    directory = [{key: row[key] for key in ("ein", "name", "city", "state", "ntee", "macro", "revenue", "periods", "tier", "score", "nyc", "la", "arts", "highCapacity")} | {"contacts": contacts_by_ein.get(row["ein"], [])} for row in target_orgs]

    organizations_by_ein = {row["ein"]: row for row in orgs}
    handoff_rows = write_email_handoff(all_contacts, ranked_by_ein, organizations_by_ein)

    profile_output = []
    colors = ["mint", "blue", "amber", "violet"]
    for index, key in enumerate(ordered_clusters):
        stat = cluster_stats[key]
        profile_output.append({
            "cluster": int(key), "tier": cluster_tier[key], "color": colors[index % len(colors)],
            "count": stat["count"], "medianRevenue": median(stat["revenue"]),
            "medianLogRevenue": median(stat["log_revenue"]), "medianPeriods": median(stat["periods"]),
            "revenueMissingShare": stat["missing"] / stat["count"], "artsShare": stat["arts"] / stat["count"],
            "marketShare": stat["market"] / stat["count"],
        })

    summary = {
        "generatedAt": date.today().isoformat(),
        "sourceNote": "Local pipeline CSV artifacts; refreshed when the site is rebuilt.",
        "organizations": len(orgs), "affiliations": artifact_stats["Individual clusters"]["rows"],
        "targetOrganizations": len(target_orgs), "targetLinkedOrganizations": len(target_eins),
        "targetAffiliations": target_affiliations,
        "peoplePreviewRows": len(people_preview),
        "nycAffiliations": city_affiliations["NYC"], "laAffiliations": city_affiliations["Los Angeles"],
        "revenueCoverage": len(orgs) - missing["revenue"], "nteeCoverage": len(orgs) - missing["ntee"],
        "publishedEmails": len(all_contacts),
        "organizationsWithPublishedEmails": len(contacts_by_ein),
        "matchedProspectEmails": sum(contact["type"] == "matched prospect person" for contact in all_contacts),
        "organizationInboxes": sum(contact["type"] == "organization inbox" for contact in all_contacts),
        "artsOrganizations": macro["A"], "revenueCutoff": cutoff,
        "stateCount": len([state for state in states if state != "Unknown"]),
        "tiers": profile_output,
        "states": [{"name": key, "count": count} for key, count in states.most_common()],
        "nteeMacro": [{"name": key, "count": count} for key, count in macro.most_common()],
        "artifacts": artifact_stats,
        "peoplePrivacy": "The static website bundle includes the first 250 ranked person–organization rows and source-linked email addresses published on organization websites.",
    }
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "organization-shortlist.json", directory)
    write_json(OUT / "people-preview.json", people_preview)
    write_json(OUT / "contact-preview.json", handoff_rows)
    print(f"Wrote {len(directory):,} organization records and {len(all_contacts):,} published contacts to {OUT}")
    print(f"Email handoff: {HANDOFF_FILE} ({len(all_contacts):,} one-email-per-row records)")
    print(f"Organizations: {len(orgs):,}; target affiliations: {target_affiliations:,}; high capacity cutoff: ${cutoff:,.0f}")


if __name__ == "__main__":
    main()
