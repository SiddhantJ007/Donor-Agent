import summary from "@/data/summary.json";
import organizationShortlist from "@/data/organization-shortlist.json";
import contactHandoff from "@/data/contact-preview.json";

export type PublishedContact = {
  email: string;
  type: string;
  matchedName: string;
  website: string;
  phone: string;
  evidenceUrl: string;
  retrievedOn: string;
  status: string;
};

export type ContactHandoffRow = {
  organization_best_rank: string | number;
  ein: string;
  organization_name: string;
  city: string;
  state: string;
  ntee_code: string;
  total_revenue: string | number;
  tax_period_count: string | number;
  tier_name: string;
  organization_score: string | number;
  contact_name: string;
  contact_type: string;
  email_address: string;
  official_website: string;
  organization_phone: string;
  evidence_url: string;
  retrieved_on: string;
  email_status: string;
};

export type OrganizationRecord = {
  ein: string;
  name: string;
  city: string;
  state: string;
  ntee: string;
  macro: string;
  revenue: number | null;
  periods: number;
  tier: string;
  score: number;
  nyc: boolean;
  la: boolean;
  arts: boolean;
  highCapacity: boolean;
  contacts: PublishedContact[];
};

export type TierProfile = {
  cluster: number;
  tier: string;
  color: string;
  count: number;
  medianRevenue: number;
  medianLogRevenue: number;
  medianPeriods: number;
  revenueMissingShare: number;
  artsShare: number;
  marketShare: number;
};

export type SiteSummary = {
  generatedAt: string;
  sourceNote: string;
  organizations: number;
  affiliations: number;
  targetOrganizations: number;
  targetLinkedOrganizations: number;
  targetAffiliations: number;
  peoplePreviewRows: number;
  nycAffiliations: number;
  laAffiliations: number;
  revenueCoverage: number;
  nteeCoverage: number;
  artsOrganizations: number;
  revenueCutoff: number;
  stateCount: number;
  tiers: TierProfile[];
  states: { name: string; count: number }[];
  nteeMacro: { name: string; count: number }[];
  artifacts: Record<string, { rows: number; columns: number; file: string }>;
  peoplePrivacy: string;
  publishedEmails: number;
  organizationsWithPublishedEmails: number;
  matchedProspectEmails: number;
  organizationInboxes: number;
};

export const siteSummary = summary as SiteSummary;
export const organizations = organizationShortlist as OrganizationRecord[];
export const emailHandoff = contactHandoff as ContactHandoffRow[];

export function downloadEmailHandoff() {
  const columns: (keyof ContactHandoffRow)[] = [
    "organization_best_rank", "ein", "organization_name", "city", "state", "ntee_code",
    "total_revenue", "tax_period_count", "tier_name", "organization_score", "contact_name",
    "contact_type", "email_address", "official_website", "organization_phone", "evidence_url",
    "retrieved_on", "email_status",
  ];
  const quote = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = [columns.join(","), ...emailHandoff.map((row) => columns.map((column) => quote(row[column])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "csaf_email_handoff.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export const formatNumber = (value: number) => new Intl.NumberFormat("en-US").format(value);
export const formatMoney = (value: number | null) => value == null ? "Not reported" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
export const share = (value: number, total: number) => total ? `${(value / total * 100).toFixed(1)}%` : "0.0%";

