"use client";

import { AppShell, Notice, PageHeader } from "@/components/app-shell";
import { useState } from "react";
import { formatNumber, siteSummary } from "@/lib/site-data";

const eventColumns = ["event_id", "campaign_id", "organization_ein", "contact_id", "event_type", "event_at", "source_system", "notes"];

export default function CampaignsPage() {
  const [message, setMessage] = useState("");
  function downloadTemplate() {
    const blob = new Blob([`${eventColumns.join(",")}\n`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "csaf_campaign_events_template.csv";
    link.click();
    URL.revokeObjectURL(url);
    setMessage("Template downloaded. Add one row per event; keep personal contact details in your approved CRM.");
  }
  return <AppShell active="/campaigns">
    <PageHeader eyebrow="CAMPAIGNS · OUTCOMES" title="Capture what happens after outreach." description="A future response model needs actual campaign results. This page provides the event format to start collecting them consistently." action={<button className="button button-primary" onClick={downloadTemplate}>Download event template ↓</button>} />
    <Notice><b>Campaign results have not been added yet.</b> Download the event template to agree on what the workflow should record.</Notice>
    {message && <div className="notice notice-info" role="status">{message}</div>}
    <section className="metric-grid campaign-metrics"><article className="metric-card"><div className="metric-top"><span>Outreach attempts</span><span className="metric-icon blue">↗</span></div><strong>—</strong><div className="metric-foot">Waiting for campaign events</div></article><article className="metric-card"><div className="metric-top"><span>Replies</span><span className="metric-icon mint">↩</span></div><strong>—</strong><div className="metric-foot">Reply rate needs delivered count</div></article><article className="metric-card"><div className="metric-top"><span>Qualified conversations</span><span className="metric-icon amber">✳</span></div><strong>—</strong><div className="metric-foot">Not recorded in IRS files</div></article><article className="metric-card"><div className="metric-top"><span>Gifts recorded</span><span className="metric-icon violet">$</span></div><strong>—</strong><div className="metric-foot">Requires CSAF CRM or campaign outcomes</div></article></section>
    <section className="dashboard-grid campaign-grid"><article className="panel campaign-empty"><div className="empty-chart"><span className="empty-icon">⌁</span><div className="empty-baseline"/></div><div className="eyebrow">RESPONSE TRENDS</div><h2>Chart activates when real events arrive</h2><p>Once campaign records are connected, compare attempts, deliveries, replies, conversations, and recorded gifts over time.</p><button className="text-button" onClick={downloadTemplate}>Get the data template →</button></article><article className="panel"><div className="eyebrow">EVENTS WORTH RECORDING</div><h2>One row for each meaningful change</h2><div className="event-list"><div><span className="event-step">1</span><div><b>Attempted</b><small>Campaign, organization, contact reference, timestamp</small></div></div><div><span className="event-step">2</span><div><b>Delivered or bounced</b><small>Delivery state and provider event reference</small></div></div><div><span className="event-step">3</span><div><b>Replied or opted out</b><small>Response category and preference date</small></div></div><div><span className="event-step">4</span><div><b>Qualified or gave</b><small>Outcome and gift date; amount only if authorized</small></div></div></div></article></section>
    <section className="panel integration-panel"><div className="integration-logo">CSV</div><div><div className="eyebrow">WORKFLOW CONNECTION</div><h3>Prepare the event contract before connecting n8n</h3><p>Use the template to agree on field names with the campaign owner. The workflow can then send events into a protected backend; this static website does not store campaign data.</p></div><div className="integration-status"><span/>Not connected</div></section>
    <div className="campaign-footnote">The prospect discovery file includes {formatNumber(siteSummary.targetAffiliations)} qualifying affiliation rows. This is not the number of messages sent or people reached.</div>
    <footer className="page-footer"><span>Do not treat uncontacted people as “did not respond.”</span><span>Outcomes are needed before supervised prediction.</span></footer>
  </AppShell>;
}

