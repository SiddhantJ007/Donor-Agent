# CSAF Donor Discovery Workspace

This workspace contains the analysis notebook, derived pipeline files, public-site contact findings, and a static Next.js dashboard. Raw filing archives, notebooks, source CSVs, and the local contact handoff CSV stay local and are excluded from Git.

## GitHub repository visibility

Use a **private GitHub repository** for the current dashboard. Its generated `web/src/data/people-preview.json` contains the first 250 real names, organization affiliations, and ranking scores, plus any exact name-matched contacts outside those rows. `web/src/data/contact-preview.json` contains published organization-site email addresses and evidence links. These JSON files are required for the static dashboard build and must be committed for Vercel to deploy it; anyone who can access the deployed site can view those contacts. Keep the repository private unless public distribution is intended.

Do not force-add ignored CSVs, notebooks, ZIP/XML archives, contact-enrichment results, or credentials. Private repositories still share their contents with invited collaborators and connected deployment services.

## Refresh dashboard data

Keep the source CSVs in the workspace root. From `web/`, run:

```bash
npm run data:build
npm run build
```

Review the generated JSON before committing. The dashboard build reads the JSON artifacts and does not need the original CSVs in GitHub or on Vercel. It also refreshes `contact_enrichment/output/csaf_email_handoff.csv` from the local contact discovery file.

## Local development

```bash
cd web
npm install
npm run dev
```

`web/next.config.ts` allows the LAN origin used for development at the time of setup. If the development machine's LAN IP changes, update `allowedDevOrigins` and restart the dev server. This setting applies only to development resources.
