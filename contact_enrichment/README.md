# Public Contact Discovery Pilot

This pilot looks for contact addresses that an organization has already published on its own website. It joins the ranked prospect list to IRS filing indexes, reads matching XML files from the local IRS archive cache, and checks each official site and a few linked contact pages.

## Run locally

From the workspace root:

```bash
python3 -m pip install -r contact_enrichment/requirements.txt
python3 contact_enrichment/discover_contacts.py --limit 10
```

Increase `--limit` to examine more organizations. Results go to `contact_enrichment/output/contact_discovery.csv`; IRS indexes are cached alongside them. Both locations are excluded from Git. The local XML archive cache is expected at `raw_xmls/archives/`.

## How the pilot handles contacts

- Reads public IRS index rows and the matching local filing XML to find each organization's website and phone number.
- Visits only that organization's own website, follows its `robots.txt`, and waits between page requests.
- Saves only email addresses actually published on that same website. It does not generate or guess addresses, test mailboxes through SMTP, or send email.
- Marks a named-person match only when the published email's local part unambiguously matches a human name already listed for that EIN.
- Saves the evidence page and retrieval date for review. A published address is source-backed, but has not been checked for deliverability or current ownership.

The script uses the IRS indexes for 2024–2026 by default. IRS indexes can be newer than the ZIP files in the local cache, so a target can show `filing_not_in_cached_archive` or fall back to an earlier locally available filing. Refresh or add the relevant IRS batch ZIPs to `raw_xmls/archives/` before rerunning in that case.

## Handoff file and dashboard

`contact_enrichment/output/contact_discovery.csv` is the unfiltered run log, including organizations where no email was found. Run `npm run data:build` from `web/` to create `contact_enrichment/output/csaf_email_handoff.csv`, with one row per unique published address and its organization, score, contact type, and evidence URL. The same build refreshes the dashboard contact data so addresses appear in organization and linked people views. Local CSV output remains Git-ignored; generated dashboard JSON includes the published contacts and is part of the static site bundle.
