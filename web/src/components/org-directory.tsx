"use client";

import { useMemo, useState } from "react";
import type { OrganizationRecord } from "@/lib/site-data";
import { downloadEmailHandoff, formatMoney, formatNumber } from "@/lib/site-data";

const PAGE_SIZE = 25;

export function OrganizationDirectory({ rows }: { rows: OrganizationRecord[] }) {
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("All markets");
  const [tier, setTier] = useState("All profiles");
  const [sector, setSector] = useState("All sectors");
  const [contactStatus, setContactStatus] = useState("Any contact status");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((row) => {
      const matchesText = !q || [row.name, row.ein, row.city, row.state, row.ntee].some((value) => value.toLowerCase().includes(q));
      const matchesCity = city === "All markets" || (city === "New York City" ? row.nyc : row.la);
      const matchesTier = tier === "All profiles" || row.tier.startsWith(tier);
      const matchesSector = sector === "All sectors" || (sector === "Arts aligned" ? row.arts : !row.arts);
      const matchesContacts = contactStatus === "Any contact status" || (contactStatus === "Published email available" ? row.contacts.length > 0 : row.contacts.length === 0);
      return matchesText && matchesCity && matchesTier && matchesSector && matchesContacts;
    });
  }, [rows, query, city, tier, sector, contactStatus]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pages);
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  function downloadCsv() {
    const columns: (keyof OrganizationRecord)[] = ["name", "ein", "city", "state", "ntee", "macro", "revenue", "periods", "tier", "score"];
    const escape = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const text = [columns.join(","), ...filtered.map((row) => columns.map((column) => escape(row[column])).join(","))].join("\n");
    const blob = new Blob([text], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "csaf_organization_review_shortlist.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return <>
    <section className="directory-controls panel" aria-label="Filter organization shortlist">
      <label className="directory-search"><span>Search shortlist</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Organization, EIN, city, state, NTEE…" /></label>
      <label><span>Market</span><select value={city} onChange={(event) => { setCity(event.target.value); setPage(1); }}><option>All markets</option><option>New York City</option><option>Los Angeles</option></select></label>
      <label><span>Profile tier</span><select value={tier} onChange={(event) => { setTier(event.target.value); setPage(1); }}><option>All profiles</option><option>Tier 1</option><option>Tier 2</option><option>Tier 3</option><option>Tier 4</option></select></label>
      <label><span>Cause area</span><select value={sector} onChange={(event) => { setSector(event.target.value); setPage(1); }}><option>All sectors</option><option>Arts aligned</option><option>Other / unknown</option></select></label>
      <label><span>Contacts</span><select value={contactStatus} onChange={(event) => { setContactStatus(event.target.value); setPage(1); }}><option>Any contact status</option><option>Published email available</option><option>No published email found</option></select></label>
      <button type="button" className="button button-secondary directory-export" onClick={downloadEmailHandoff}>Download email handoff <span>↓</span></button>
      <button type="button" className="button button-primary directory-export" onClick={downloadCsv}>Download filtered CSV <span>↓</span></button>
    </section>
    <div className="directory-toolbar-note"><span>Organization review list</span><span>Search by name, EIN, location, cause, or profile</span><b>{formatNumber(filtered.length)} matching organizations</b></div>
    <div className="panel org-table-panel">
      <div className="table-scroll"><table className="org-table"><thead><tr><th>Organization</th><th>Location</th><th>Cause</th><th>Annual revenue</th><th>Filing years</th><th>Profile</th><th>Review score</th><th>Published contacts</th></tr></thead>
        <tbody>{visible.map((row) => <tr key={row.ein}><td><b>{row.name}</b><small>EIN {row.ein}</small></td><td>{row.city || "—"}, {row.state || "—"}</td><td><span className={`cause-pill ${row.arts ? "cause-arts" : ""}`}>{row.arts ? "Arts aligned" : row.macro || "Unknown"}</span>{row.ntee && <small>NTEE {row.ntee}</small>}</td><td>{formatMoney(row.revenue)}</td><td>{row.periods}</td><td><span className={`tier-tag ${row.tier.startsWith("Tier 1") ? "mint" : row.tier.startsWith("Tier 2") ? "blue" : row.tier.startsWith("Tier 3") ? "amber" : "violet"}`}>{row.tier.split("—")[1]?.split(":")[0]?.trim() || row.tier}</span></td><td><b className="review-score">{row.score.toFixed(1)}</b><small>out of 100</small></td><td>{row.contacts.length ? <details className="contact-details"><summary>{row.contacts.length} email{row.contacts.length === 1 ? "" : "s"}</summary><div className="contact-details-list">{row.contacts.map((contact) => <div key={`${contact.email}-${contact.type}`}><a href={`mailto:${contact.email}`}>{contact.email}</a>{contact.matchedName && <small>{contact.matchedName} · matched prospect</small>}{!contact.matchedName && <small>{contact.type}</small>}{contact.evidenceUrl && <a className="contact-source" href={contact.evidenceUrl} target="_blank" rel="noreferrer">Source page ↗</a>}</div>)}</div></details> : <span className="contact-none">Not found</span>}</td></tr>)}</tbody>
      </table></div>
      {!visible.length && <div className="table-empty">No organizations match those filters. Try broadening your search.</div>}
      <nav className="table-pagination" aria-label="Organization results pages"><span aria-live="polite">Showing {filtered.length ? formatNumber((currentPage - 1) * PAGE_SIZE + 1) : 0}–{formatNumber(Math.min(currentPage * PAGE_SIZE, filtered.length))} of {formatNumber(filtered.length)}</span><div><button type="button" onClick={() => setPage((current) => Math.max(1, Math.min(current, pages) - 1))} disabled={currentPage === 1} aria-label="Previous page">← Previous</button><span aria-live="polite">Page {currentPage} of {pages}</span><button type="button" onClick={() => setPage((current) => Math.min(pages, Math.min(current, pages) + 1))} disabled={currentPage === pages} aria-label="Next page">Next →</button></div></nav>
    </div>
    <p className="table-disclaimer">Published addresses are shown with their source pages. A person match appears only when the published name matches a prospect record; email delivery has not been verified.</p>
  </>;
}

