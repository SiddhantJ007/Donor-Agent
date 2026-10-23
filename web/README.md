# CSAF Prospect Workspace

Static Next.js dashboard built from local IRS pipeline data. Generated files in `src/data/` provide aggregate metrics, the organization shortlist, a 250-row people preview, and source-linked published contacts.

## Local development

```bash
npm install
npm run dev
```

The LAN IP in `next.config.ts` is specific to the current development network. If it changes, update `allowedDevOrigins` and restart `next dev`.

## Refresh derived dashboard data

The pipeline CSVs are expected in the parent workspace and are deliberately excluded from Git. From this directory, run:

```bash
npm run data:build
npm run build
```

The generated `src/data/*.json` files are required for the current static build. They include the first 250 ranked person–organization rows with names and scores, any exact name-matched contacts outside those rows, and published email addresses found on organization websites. Keep the repository private if those rows and contacts should not be publicly downloadable.

## Vercel

Set the project root to `web` and use `npm run build`. The static dashboard does not require a database or runtime API. Vercel uses the JSON files committed to the repository; refresh them locally and redeploy when the pipeline data changes.

## Data boundaries

The repository excludes the source CSVs, raw IRS ZIP/XML archives, notebook, and local email-enrichment outputs. The organization review list, 250-row people preview, and published contact directory are included in the website data bundle. Campaign event metrics remain empty until a campaign system supplies outcomes. Published email addresses are not mailbox-verified.
