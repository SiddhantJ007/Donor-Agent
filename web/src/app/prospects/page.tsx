"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { AppShell, PageHeader } from "@/components/app-shell";
import { downloadEmailHandoff, formatNumber, siteSummary, type PublishedContact } from "@/lib/site-data";
import peopleData from "@/data/people-preview.json";

type PersonRow = {
  rank: number; name: string; ein: string; organization: string; city: string; state: string;
  tier: string; score: number; revenue: number | null; periods: number; ntee: string; explanations: string[];
  contacts: PublishedContact[];
};
const people = peopleData as PersonRow[];
const PAGE_SIZE = 25;

export default function ProspectsPage() {
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return needle ? people.filter((row) => [row.name, row.organization, row.city, row.state, row.ein].some((item) => item.toLowerCase().includes(needle))) : people;
  }, [query]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const activePage = Math.min(page, pageCount);
  const visible = filtered.slice((activePage - 1) * PAGE_SIZE, activePage * PAGE_SIZE);

  function downloadCsv() {
    const columns = ["rank", "name", "ein", "organization", "city", "state", "tier", "score", "revenue", "periods", "ntee", "explanations"] as const;
    const quote = (value: unknown) => `"${String(Array.isArray(value) ? value.join("; ") : value ?? "").replaceAll('"', '""')}"`;
    const csv = [columns.join(","), ...filtered.map((row) => columns.map((column) => quote(row[column])).join(","))].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "csaf_ranked_people_preview.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return <AppShell active="/prospects">
    <PageHeader eyebrow="PEOPLE · LINKED TO ORGANIZATIONS" title="Explore the people in the ranked file." description="These names and affiliations come from the saved IRS filing export. Search the first 250 ranked rows plus every person with a published name-matched address, review organization contacts, and download the available handoff list." action={<Link href="/organizations" className="button button-secondary">Organization directory ↗</Link>} />
    <section className="people-summary-grid"><article className="panel people-summary-card"><span>Ranked affiliation records</span><strong>{formatNumber(siteSummary.targetAffiliations)}</strong><small>Distinct person–organization pairs in the Cell 7 export</small></article><article className="panel people-summary-card"><span>Organizations represented</span><strong>{formatNumber(siteSummary.targetLinkedOrganizations)}</strong><small>Organizations with at least one ranked person</small></article><article className="panel people-summary-card"><span>Published email addresses</span><strong>{formatNumber(siteSummary.publishedEmails)}</strong><small>Found on the listed organizations’ websites</small></article><article className="panel people-summary-card"><span>Matched prospect names</span><strong>{formatNumber(siteSummary.matchedProspectEmails)}</strong><small>Published address matched to a listed person</small></article></section>
    <section className="panel people-controls"><label><span>Search these records</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Name, organization, EIN, or location"/></label><button type="button" className="button button-secondary" onClick={downloadEmailHandoff}>Download email handoff ↓</button><button type="button" className="button button-primary" onClick={downloadCsv}>Download matching people ↓</button></section>
    <div className="directory-toolbar-note"><span>Ranked people · saved notebook output</span><b>{formatNumber(filtered.length)} matching rows</b></div>
    <div className="panel org-table-panel"><div className="table-scroll"><table className="org-table people-table"><thead><tr><th>Rank</th><th>Person</th><th>Organization</th><th>Location</th><th>Tier</th><th>Review score</th><th>Filing periods</th><th>Why it ranked</th><th>Published contacts</th></tr></thead><tbody>{visible.map((row) => { const direct = row.contacts.filter((contact) => contact.type === "matched prospect person" && contact.matchedName.trim().toLowerCase() === row.name.trim().toLowerCase()); return <tr key={`${row.rank}-${row.ein}-${row.name}`}><td>{row.rank}</td><td><b>{row.name}</b><small>EIN {row.ein}</small></td><td>{row.organization}<small>NTEE {row.ntee || "Not listed"}</small></td><td>{row.city}, {row.state}</td><td><span className="tier-tag mint">{row.tier.split("—")[1]?.split(":")[0]?.trim()}</span></td><td><b className="review-score">{row.score.toFixed(1)}</b><small>out of 100</small></td><td>{row.periods}</td><td>{row.explanations.join(" · ")}</td><td>{row.contacts.length ? <details className="contact-details"><summary>{direct.length ? `${direct.length} person match` : `${row.contacts.length} organization contact${row.contacts.length === 1 ? "" : "s"}`}</summary><div className="contact-details-list">{row.contacts.map((contact) => <div key={`${contact.email}-${contact.type}`}><a href={`mailto:${contact.email}`}>{contact.email}</a><small>{contact.type === "matched prospect person" ? `Matched to ${contact.matchedName}` : contact.type}</small>{contact.evidenceUrl && <a className="contact-source" href={contact.evidenceUrl} target="_blank" rel="noreferrer">Source page ↗</a>}</div>)}</div></details> : <span className="contact-none">—</span>}</td></tr>; })}</tbody></table></div>
      {!visible.length && <div className="table-empty">No matching rows. Try a shorter name or organization search.</div>}
      <div className="table-pagination"><span>Showing {filtered.length ? formatNumber((activePage - 1) * PAGE_SIZE + 1) : 0}–{formatNumber(Math.min(activePage * PAGE_SIZE, filtered.length))} of {formatNumber(filtered.length)}</span><div><button type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={activePage === 1}>← Previous</button><span>Page {activePage} of {pageCount}</span><button type="button" onClick={() => setPage((current) => Math.min(pageCount, current + 1))} disabled={activePage === pageCount}>Next →</button></div></div>
    </div>
    <p className="table-disclaimer">Email addresses are listed on organization websites. A person match is shown only where the published name matches the prospect record; addresses have not been mailbox-verified.</p>
    <footer className="page-footer"><span>Showing actual names and rows from the saved ranked export.</span><span><Link href="/data">Data file summaries →</Link></span></footer>
  </AppShell>;
}

