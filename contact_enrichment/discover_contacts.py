#!/usr/bin/env python3
"""Find publicly posted contacts for a small set of ranked organizations.

The script joins ranked EINs to IRS e-file indexes, reads just the matching
local XML filings, and checks the organizations' own websites for published
email addresses. It does not guess addresses, probe mail servers, or send mail.
All downloaded indexes and CSV output are written under the ignored output/ dir.
"""

from __future__ import annotations

import argparse
import csv
import html
import ipaddress
import re
import ssl
import subprocess
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.robotparser import RobotFileParser

import certifi


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = ROOT / "csaf_ranked_donor_prospects.csv"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output"
INDEX_BASE = "https://apps.irs.gov/pub/epostcard/990/xml"
USER_AGENT = "CSAF-Contact-Research/0.1 (public organization website review)"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
EMAIL_RE = re.compile(r"(?i)(?<![\w.+-])[\w.+-]{1,64}@[\w.-]+\.[a-z]{2,24}(?![\w.-])")
ROLE_NAMES = {
    "admin", "advancement", "contact", "development", "donate", "donations", "donor",
    "giving", "hello", "info", "office", "outreach", "partnership", "partnerships",
    "philanthropy", "plannedgiving", "support",
}
SKIP_EMAIL_LOCALS = {"someone", "yourname", "example", "test", "email"}
CONTACT_WORDS = ("contact", "about", "staff", "leadership", "board", "team", "giving", "development", "donate")


@dataclass
class ContactPage(HTMLParser):
    """Collect page text and same-host links that may lead to contact details."""

    text_parts: list[str]
    links: list[tuple[str, str]]

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts = []
        self.links = []
        self._anchor_href = ""
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._anchor_href = next((value or "" for key, value in attrs if key.lower() == "href"), "")
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self._anchor_href:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._anchor_href:
            self.links.append((self._anchor_href, " ".join(self._anchor_text)))
            self._anchor_href = ""
            self._anchor_text = []


def download(url: str, destination: Path, timeout: int = 60) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response, destination.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            out.write(chunk)


def load_index(year: int, index_dir: Path) -> Path:
    path = index_dir / f"index_{year}.csv"
    if not path.exists():
        download(f"{INDEX_BASE}/{year}/index_{year}.csv", path)
        print(f"Downloaded IRS {year} index: {path.stat().st_size / 1_000_000:.1f} MB")
    return path


def pick_targets(path: Path, limit: int) -> list[dict[str, str]]:
    targets: list[dict[str, str]] = []
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            ein = (row.get("ein") or "").strip().replace("-", "").zfill(9)
            if not ein or ein == "000000000" or ein in seen:
                continue
            seen.add(ein)
            targets.append({
                "ein": ein,
                "organization_name": (row.get("organization_name") or "").strip(),
                "city": (row.get("city") or "").strip(),
                "state": (row.get("state") or "").strip(),
                "rank": (row.get("outreach_rank") or "").strip(),
                "score": (row.get("outreach_priority_score") or "").strip(),
            })
            if len(targets) >= limit:
                break
    return targets


def index_filing_history(index_paths: list[Path], target_eins: set[str]) -> dict[str, list[dict[str, str]]]:
    filings: dict[str, dict[tuple[str, str], dict[str, str]]] = {ein: {} for ein in target_eins}
    for path in index_paths:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                ein = (row.get("EIN") or "").strip().zfill(9)
                if ein not in target_eins:
                    continue
                key = (row.get("XML_BATCH_ID", ""), row.get("OBJECT_ID", ""))
                filings[ein][key] = row
    histories = {}
    for ein, by_id in filings.items():
        histories[ein] = sorted(
            by_id.values(),
            key=lambda row: (row.get("TAX_PERIOD", ""), row.get("SUB_DATE", ""), row.get("XML_BATCH_ID", "")),
            reverse=True,
        )
    return histories


def local_tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1].lower()


def filing_details(filing: dict[str, str], archive_dir: Path) -> tuple[list[str], list[str], str]:
    batch = (filing.get("XML_BATCH_ID") or "").strip()
    object_id = (filing.get("OBJECT_ID") or "").strip()
    archive = archive_dir / f"{batch}.zip"
    member = f"{object_id}_public.xml"
    if not archive.exists():
        return [], [], f"archive_missing:{archive.name}"
    result = subprocess.run(
        ["7zz", "e", "-so", str(archive), member],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return [], [], f"xml_extract_failed:{result.stderr.decode(errors='replace')[-180:]}"
    if not result.stdout:
        return [], [], "filing_not_in_cached_archive"
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as exc:
        return [], [], f"xml_parse_failed:{exc}"
    websites = []
    phones = []
    for item in root.iter():
        tag = local_tag(item)
        value = (item.text or "").strip()
        if tag == "websiteaddresstxt" and value and value.upper() not in {"N/A", "NA", "NONE"}:
            websites.append(value)
        elif tag == "phonenum" and value:
            phones.append(value)
    return list(dict.fromkeys(websites)), list(dict.fromkeys(phones)), "filing_read"


def normalize_website(value: str) -> str:
    value = html.unescape(value.strip()).rstrip(".,;)")
    if not value:
        return ""
    if not re.match(r"^https?://", value, re.I):
        value = "https://" + value.lstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if not ip.is_global:
            return ""
    except ValueError:
        pass
    # Filing XML sometimes capitalizes the host; lowercase it for tidy evidence URLs.
    netloc = parsed.netloc.lower()
    return urllib.parse.urlunparse(parsed._replace(netloc=netloc, fragment=""))


def same_host(first: str, second: str) -> bool:
    a = (urllib.parse.urlparse(first).hostname or "").lower().removeprefix("www.")
    b = (urllib.parse.urlparse(second).hostname or "").lower().removeprefix("www.")
    return bool(a and a == b)


def allowed_by_robots(url: str, robots_cache: dict[str, tuple[RobotFileParser, str]]) -> tuple[bool, str]:
    parsed = urllib.parse.urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in robots_cache:
        parser = RobotFileParser()
        parser.set_url(urllib.parse.urljoin(origin, "/robots.txt"))
        try:
            request = urllib.request.Request(parser.url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=8, context=SSL_CONTEXT) as response:
                parser.parse(response.read().decode("utf-8", errors="replace").splitlines())
            result = "robots_allowed"
        except urllib.error.HTTPError as exc:
            # A missing robots.txt is treated as no published crawl restriction.
            if exc.code == 404:
                parser.parse([])
                result = "robots_file_missing"
            else:
                parser.parse(["User-agent: *", "Disallow: /"])
                result = f"robots_http_{exc.code}"
        except Exception:
            # If robots.txt cannot be checked, skip rather than crawl blindly.
            parser.parse(["User-agent: *", "Disallow: /"])
            result = "robots_fetch_failed"
        robots_cache[origin] = (parser, result)
    parser, result = robots_cache[origin]
    if not parser.can_fetch(USER_AGENT, url):
        if result == "robots_fetch_failed" or result.startswith("robots_http_"):
            return False, result
        return False, "robots_disallowed"
    return True, result


def fetch_page(url: str, robots_cache: dict[str, tuple[RobotFileParser, str]], delay: float, last_request: list[float]) -> tuple[str, str]:
    allowed, robots_status = allowed_by_robots(url, robots_cache)
    if not allowed:
        return "", robots_status
    wait = delay - (time.monotonic() - last_request[0])
    if last_request[0] and wait > 0:
        time.sleep(wait)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(request, timeout=12, context=SSL_CONTEXT) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if "html" not in content_type and "text/plain" not in content_type:
                return "", "non_html"
            body = response.read(1_500_000).decode("utf-8", errors="replace")
            last_request[0] = time.monotonic()
            return body, "ok"
    except urllib.error.HTTPError as exc:
        last_request[0] = time.monotonic()
        return "", f"http_{exc.code}"
    except Exception as exc:
        last_request[0] = time.monotonic()
        return "", f"fetch_error:{type(exc).__name__}"


def simplify(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", value).lower() if char.isalnum())


def person_email_matches(email: str, prospect_names: set[str]) -> str:
    local = simplify(email.split("@", 1)[0].split("+", 1)[0])
    matches = []
    for full_name in prospect_names:
        words = [simplify(part) for part in re.findall(r"[\w'-]+", full_name) if simplify(part)]
        if len(words) < 2:
            continue
        first, last = words[0], words[-1]
        last_variants = {last}
        # Let a published first-initial + final surname match a hyphenated last name.
        last_variants.update(part for part in re.split(r"[-']+", full_name.split()[-1]) if part)
        aliases = {first + surname for surname in last_variants}
        aliases.update(first[:1] + simplify(surname) for surname in last_variants)
        aliases.update(simplify(surname) + first[:1] for surname in last_variants)
        if local in aliases:
            matches.append(full_name)
    return matches[0] if len(matches) == 1 else ""


def extract_emails(body: str, website: str) -> list[str]:
    normalized = html.unescape(body)
    normalized = re.sub(r"\s*(?:\[at\]|\(at\)|\{at\})\s*", "@", normalized, flags=re.I)
    normalized = re.sub(r"\s*(?:\[dot\]|\(dot\)|\{dot\})\s*", ".", normalized, flags=re.I)
    result = []
    for email in EMAIL_RE.findall(normalized):
        email = email.strip(".,;:!?<>()[]{}'\"").lower()
        domain = email.rsplit("@", 1)[-1]
        local = email.split("@", 1)[0].split("+", 1)[0]
        website_domain = (urllib.parse.urlparse(website).hostname or "").lower().removeprefix("www.")
        if (domain == website_domain and local not in SKIP_EMAIL_LOCALS
                and not domain.endswith((".png", ".jpg", ".gif", ".svg"))):
            result.append(email)
    return list(dict.fromkeys(result))


def candidate_pages(homepage: str, body: str, cap: int) -> list[str]:
    parser = ContactPage()
    parser.feed(body)
    candidates = []
    for href, label in parser.links:
        text = f"{href} {label}".lower()
        if not any(word in text for word in CONTACT_WORDS):
            continue
        absolute = urllib.parse.urljoin(homepage, href)
        if absolute.startswith(("mailto:", "tel:")) or not same_host(homepage, absolute):
            continue
        parsed = urllib.parse.urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        clean = urllib.parse.urlunparse(parsed._replace(query="", fragment=""))
        if clean not in candidates and clean != homepage:
            candidates.append(clean)
        if len(candidates) >= cap:
            break
    return candidates


def role_or_person(email: str) -> str:
    local = email.split("@", 1)[0].lower().split("+", 1)[0]
    return "organization inbox" if local in ROLE_NAMES else "published site address"


def prospect_names_by_ein(path: Path, target_eins: set[str]) -> dict[str, set[str]]:
    names: dict[str, set[str]] = {ein: set() for ein in target_eins}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            ein = (row.get("ein") or "").strip().replace("-", "").zfill(9)
            name = (row.get("human_name") or "").strip()
            if ein in names and name:
                names[ein].add(name)
    return names


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--limit", type=int, default=50, help="Number of distinct ranked organizations to examine")
    parser.add_argument("--years", type=int, nargs="+", default=[2024, 2025, 2026])
    parser.add_argument("--delay", type=float, default=1.25, help="Minimum seconds between page requests per organization website")
    parser.add_argument("--pages-per-site", type=int, default=4, help="Homepage plus at most this many contact-related pages")
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_OUTPUT / "indexes")
    parser.add_argument("--archive-dir", type=Path, default=ROOT / "raw_xmls" / "archives")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT / "contact_discovery.csv")
    args = parser.parse_args()
    if args.limit < 1 or args.delay < 0 or args.pages_per_site < 1:
        parser.error("--limit and --pages-per-site must be positive; --delay cannot be negative")

    targets = pick_targets(args.targets, args.limit)
    if not targets:
        raise SystemExit("No ranked EINs found in the target CSV")
    indexes = [load_index(year, args.index_dir) for year in args.years]
    filing_history = index_filing_history(indexes, {row["ein"] for row in targets})
    args.output.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "rank", "ein", "organization_name", "city", "state", "priority_score",
        "tax_period", "filing_submitted", "official_website", "organization_phone",
        "email_address", "contact_type", "matched_prospect_name", "evidence_url", "retrieved_on", "status",
    ]
    prospect_names = prospect_names_by_ein(args.targets, {row["ein"] for row in targets})
    found_total = 0
    prospect_match_total = 0
    org_inbox_total = 0
    site_total = 0
    with args.output.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=columns)
        writer.writeheader()
        for i, target in enumerate(targets, start=1):
            filings = filing_history.get(target["ein"], [])
            filing = None
            websites: list[str] = []
            phones: list[str] = []
            extraction_status = "no_index_match"
            # Indexes can be newer than the locally cached ZIPs. Walk filings in
            # recency order until we find a local XML; prefer the newest one with
            # a usable website, falling back to the newest readable filing.
            for candidate in filings:
                candidate_websites, candidate_phones, status = filing_details(candidate, args.archive_dir)
                if status != "filing_read":
                    extraction_status = status
                    continue
                if filing is None:
                    filing, phones, extraction_status = candidate, candidate_phones, status
                if candidate_websites:
                    filing, websites, phones, extraction_status = candidate, candidate_websites, candidate_phones, status
                    break
            base = {
                "rank": target["rank"], "ein": target["ein"], "organization_name": target["organization_name"],
                "city": target["city"], "state": target["state"], "priority_score": target["score"],
                "tax_period": filing.get("TAX_PERIOD", "") if filing else "",
                "filing_submitted": filing.get("SUB_DATE", "") if filing else "",
                "official_website": "", "organization_phone": "", "email_address": "",
                "contact_type": "", "matched_prospect_name": "", "evidence_url": "", "retrieved_on": date.today().isoformat(),
                "status": "no_index_match",
            }
            if not filings:
                writer.writerow(base)
                continue
            if not filing:
                base["status"] = extraction_status
                writer.writerow(base)
                continue
            base["organization_phone"] = "; ".join(phones)
            base["status"] = extraction_status
            normalized_sites = list(dict.fromkeys(filter(None, (normalize_website(site) for site in websites))))
            if not normalized_sites:
                if extraction_status == "filing_read":
                    base["status"] = "no_website_in_latest_filing"
                writer.writerow(base)
                continue

            for site in normalized_sites:
                site_total += 1
                base["official_website"] = site
                robots_cache: dict[str, tuple[RobotFileParser, str]] = {}
                last_request = [0.0]
                homepage, home_status = fetch_page(site, robots_cache, args.delay, last_request)
                if not homepage:
                    base["status"] = home_status
                    writer.writerow(base)
                    continue
                pages = [(site, homepage)]
                for page_url in candidate_pages(site, homepage, args.pages_per_site - 1):
                    content, status = fetch_page(page_url, robots_cache, args.delay, last_request)
                    if content:
                        pages.append((page_url, content))
                emails: dict[str, str] = {}
                for page_url, content in pages:
                    for email in extract_emails(content, site):
                        emails.setdefault(email, page_url)
                if emails:
                    for email, evidence_url in emails.items():
                        row = dict(base)
                        matched_name = person_email_matches(email, prospect_names.get(target["ein"], set()))
                        contact_type = "matched prospect person" if matched_name else role_or_person(email)
                        row.update({
                            "email_address": email,
                            "contact_type": contact_type,
                            "matched_prospect_name": matched_name,
                            "evidence_url": evidence_url,
                            "status": "published_on_official_site_not_mailbox_verified",
                        })
                        writer.writerow(row)
                        found_total += 1
                        prospect_match_total += int(bool(matched_name))
                        org_inbox_total += int(contact_type == "organization inbox")
                else:
                    base["status"] = "site_checked_no_published_email"
                    writer.writerow(base)
            print(f"[{i}/{len(targets)}] {target['ein']} {target['organization_name']}: checked {len(normalized_sites)} website(s)")

    print(f"Organizations examined: {len(targets)}; filing website(s): {site_total}; same-domain published email rows: {found_total}")
    print(f"Exact ranked-person name matches: {prospect_match_total}; organization inboxes: {org_inbox_total}")
    print(f"Results saved locally to: {args.output}")
    print("An address listed on a page is source-backed, not proof the mailbox accepts mail.")


if __name__ == "__main__":
    main()
