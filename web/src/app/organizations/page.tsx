"use client";

import Link from "next/link";
import { AppShell, Notice, PageHeader } from "@/components/app-shell";
import { OrganizationDirectory } from "@/components/org-directory";
import { organizations, siteSummary, formatNumber, downloadEmailHandoff } from "@/lib/site-data";

export default function OrganizationsPage() {
  return <AppShell active="/organizations">
    <PageHeader eyebrow="PROSPECTS · ORGANIZATIONS" title="Explore the organization shortlist." description="Search and filter the real organization records selected from the notebook pipeline. The shortlist can be downloaded for review." action={<a className="button button-secondary" href="/data">See data details <span>↗</span></a>} />
    <Notice><b>{formatNumber(siteSummary.targetOrganizations)} organizations</b> match the review rule: exact New York City or Los Angeles location, plus Arts alignment or top-quartile reported revenue. The saved Cell 7 output links {formatNumber(siteSummary.targetLinkedOrganizations)} organizations to {formatNumber(siteSummary.targetAffiliations)} ranked person–organization records.</Notice>
    <section className="contact-handoff-card panel"><div><div className="eyebrow">PUBLIC CONTACTS · ORGANIZATION WEBSITES</div><h2>{formatNumber(siteSummary.publishedEmails)} published email addresses across {formatNumber(siteSummary.organizationsWithPublishedEmails)} organizations</h2><p>Includes named-person matches and general organization contacts, with source pages and review details for Anthony’s team.</p></div><button type="button" className="button button-primary" onClick={downloadEmailHandoff}>Download email handoff CSV ↓</button></section>
    <section className="directory-tier-grid">{siteSummary.tiers.map((profile) => <article className="panel directory-tier" key={profile.cluster}><div><span className={`tier-dot ${profile.color}`} /><span className={`tier-tag ${profile.color}`}>{profile.tier.split("—")[1]?.split(":")[0]?.trim()}</span></div><strong>{formatNumber(profile.count)}</strong><small>organizations · {((profile.count / siteSummary.organizations) * 100).toFixed(1)}% of total</small><div className="tier-share-track"><i className={profile.color} style={{ width: `${profile.count / siteSummary.organizations * 100}%` }} /></div></article>)}</section>
    <OrganizationDirectory rows={organizations} />
    <footer className="page-footer"><span>Ranked person records are available in the People section.</span><span><Link href="/prospects">Open people list →</Link></span></footer>
  </AppShell>;
}

