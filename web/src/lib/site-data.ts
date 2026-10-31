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
  sharedOrganizationCount: number;
};

export type ContactHandoffRow = {
  email_address: string;
  primary_organization_best_rank: string | number;
  primary_ein: string;
  primary_organization_name: string;
  primary_city: string;
  primary_state: string;
  primary_ntee_code: string;
  primary_total_revenue: string | number;
  primary_tax_period_count: string | number;
  primary_tier_name: string;
  primary_organization_score: string | number;
  associated_organization_count: number;
  associated_organizations: string;
  contact_names: string;
  contact_types: string;
  official_websites: string;
  organization_phones: string;
  evidence_urls: string;
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
  emailOrganizationAssociations: number;
  sharedEmailAddresses: number;
  organizationsWithPublishedEmails: number;
  contactOrganizationsChecked: number;
  contactOrganizationsWithEmail: number;
  contactSiteCheckedNoEmail: number;
  contactNeedsRetry: number;
  contactRetrievedAt: string;
  matchedProspectEmails: number;
  organizationInboxes: number;
};

export const siteSummary = summary as SiteSummary;
export const organizations = organizationShortlist as OrganizationRecord[];
export const emailHandoff = contactHandoff as ContactHandoffRow[];

export function downloadEmailHandoff() {
  const columns: (keyof ContactHandoffRow)[] = [
    "email_address", "primary_organization_best_rank", "primary_ein", "primary_organization_name",
    "primary_city", "primary_state", "primary_ntee_code", "primary_total_revenue", "primary_tax_period_count",
    "primary_tier_name", "primary_organization_score", "associated_organization_count", "associated_organizations",
    "contact_names", "contact_types", "official_websites", "organization_phones", "evidence_urls", "retrieved_on", "email_status",
  ];
  const quote = (value: unknown) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const csv = [columns.join(","), ...emailHandoff.map((row) => columns.map((column) => quote(row[column])).join(","))].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "csaf_unique_email_recipients.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export const formatNumber = (value: number) => new Intl.NumberFormat("en-US").format(value);
export const formatMoney = (value: number | null) => value == null ? "Not reported" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
export const share = (value: number, total: number) => total ? `${(value / total * 100).toFixed(1)}%` : "0.0%";

