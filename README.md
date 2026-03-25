# Real Estate Intelligence Map

מערכת מודיעין פרויקטים למגורים של חברות נדל"ן ציבוריות בישראל.

המטרה היא לבנות מערכת שמחלצת, מנרמלת ומציגה ברמת פרויקט נתונים מתוך דו"חות של חברות ציבוריות, כולל מפה אינטראקטיבית, סינון מתקדם, מסכי פרויקט, וממשק אדמין פנימי לניהול שיוך מיקום, כתובות, סיווגים ובקרת איכות.

## מה יש בפרויקט

- מפה אינטראקטיבית מבוססת Mapbox
- בסיס נתונים פרויקטלי על חברות נדל"ן למגורים
- מנוע חילוץ וטיוב נתונים מתוך דו"חות PDF
- ממשק ציבורי לחיפוש, סינון והשוואה
- ממשק אדמין פנימי לניהול מיקומים, סיווגים ו-QA

## מסמכי אפיון

כל מסמכי האפיון נמצאים תחת תיקיית `docs`:

- [PRD](./docs/PRD.md)
- [DB Schema](./docs/DB_SCHEMA.md)
- [UX Flows](./docs/UX_FLOWS.md)
- [Backlog & Sprints](./docs/BACKLOG_SPRINTS.md)
- [Normalization Rules](./docs/NORMALIZATION_RULES.md)
- [API Contract](./docs/API_CONTRACT.md)

## עקרונות ליבה

- המערכת מתמקדת רק בנדל"ן למגורים
- נשמרים כל השדות וכל הסיווגים כבר בגרסה הראשונה
- קיימת הפרדה קשיחה בין יזמי רגיל, מסלולים ממשלתיים והתחדשות עירונית
- המפה אינה מקור האמת; מקור האמת הוא שכבת נתונים קנונית עם שיוך למקור בדו"ח
- קיימת שכבת אדמין פנימית לשיוך מיקום, ריבוי כתובות, איחוד פרויקטים ותיקון סיווגים

## סטטוס

הפרויקט נמצא בשלב אפיון ותכנון ארכיטקטורה לפני פירוק למשימות פיתוח.

## שלב הבא

השלב הבא הוא להתחיל לממש את ה־backlog לפי הספרינטים שהוגדרו במסמך:
`docs/BACKLOG_SPRINTS.md`

## Technical Setup

### Working core product

This repository is currently optimized around a practical ingestion-and-database flow:

- source report registry
- born-digital PDF reading
- extraction into staging
- admin review of report candidates
- canonical projects and project snapshots
- filtering, export, and database-facing analysis

The following areas are intentionally de-emphasized in the current phase:

- map-first browsing polish
- experimental multi-backend document conversion
- OCR-heavy workflows
- parser benchmark tooling as part of the main admin path
- advanced public UX work that does not improve ingestion, review, or database quality

### Repository structure

- `apps/web` - Next.js + TypeScript public/admin UI shell
- `apps/api` - FastAPI service with versioned routers
- `packages/shared` - shared frontend enums and UI-facing types
- `infra/db/migrations` - PostgreSQL/PostGIS bootstrap SQL
- `docs` - product, schema, UX, normalization, and API docs

### Local development

1. Copy `.env.example` to `.env`
2. Copy `apps/api/.env.example` to `apps/api/.env`
3. Copy `apps/web/.env.example` to `apps/web/.env.local`
4. Start the stack with `docker compose up --build`
5. Seed the curated real Phase 2 dataset with `docker compose exec api python -m app.seed`

If you already initialized the Postgres volume before the Phase 2 migration changes, recreate the DB volume once with `docker compose down -v` and then start the stack again.

### Service URLs

- Web: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Phase 3 Notes

- API container startup now applies pending SQL migrations automatically before FastAPI boots.
- Seed the curated public residential dataset with `docker compose exec api python -m app.seed`.
- Run API tests with `python -m pytest apps/api/tests -q`.
- Run web validation with `npm run typecheck --workspace @real-estat-map/web` and `npm run build --workspace @real-estat-map/web`.

### Admin Review Tools

- Admin project queue: `http://localhost:3000/admin/projects`
- Admin project detail: `http://localhost:3000/admin/projects/<project-id>`
- Admin intake queue: `http://localhost:3000/admin/intake`
- Admin source registry: `http://localhost:3000/admin/sources`
- Admin source workspace: `http://localhost:3000/admin/sources/<report-id>`
- Admin is now organized around:
  - Projects as the core canonical workspace
  - Intake as the candidate review queue
  - Sources as the supporting report registry
- Current working ingestion flow:
  - create a source report
  - run extraction into staging
  - review candidates in the source workspace or intake
  - match an existing project or mark a new one
  - publish into canonical projects and snapshots
  - inspect the resulting database via `/projects` and CSV export

### Phase 4 Manual Ingestion Bridge

- Source registry: `http://localhost:3000/admin/sources`
- Source workspace: `http://localhost:3000/admin/sources/<report-id>`
- Use the report workspace to:
  - register or update a source report record
  - create staging project candidates manually
  - add field-level and address-level staging rows
  - review match suggestions against canonical projects
  - compare incoming staged values with canonical values
  - publish approved candidates into canonical project, snapshot, address, provenance, and audit tables
- The staging layer is separate from canonical data. Admin entry writes into staging first; canonical tables are only updated by the explicit publish action.
- The Phase 2 seed flow remains valid. Run `docker compose exec api python -m app.seed` to load the baseline dataset before using manual ingestion.

### Implemented In Phase 3

- Public project detail pages with provenance, metrics, addresses, and history
- Public company detail pages with coverage summaries and project drill-down
- URL-driven research filters plus CSV export
- Real map research panel backed by `/api/v1/map/projects`
- Admin review surface with DB persistence and audit trail
- Endpoint contract tests for core public/admin API routes

### Still Deferred For The Parser/Ingestion Phase

- PDF parsing and extraction pipelines
- Automated report ingestion and upload workflows
- OCR or AI summarization layers
- Authentication and permissions
- Production deployment pipeline

### Phase 4 Status

- Implemented:
  - report registry metadata and admin CRUD
  - staging reports, project candidates, field candidates, address candidates, and review queue tables
  - candidate matching states and candidate publish flow with audit logging
  - manual compare view and snapshot diff summary in admin
- Still deferred for the next ingestion phase:
  - automated PDF parsing or OCR
  - LLM extraction
  - bulk upload automation
  - advanced conflict resolution and multi-review workflows

### Next Sprint Status

- Implemented:
  - stronger alias handling for canonical projects, including source/manual/system alias types and active/inactive alias state
  - rules-based candidate match suggestion persistence using company, name similarity, city, neighborhood, and address overlap
  - duplicate detection plus safe admin merge flow with audit trail
  - coverage registry and admin coverage dashboard for broader backfill operations
  - snapshot chronology checks that flag duplicate-date and out-of-order history rows
  - hardened admin search across canonical name, alias, company, city, and address text
- Admin operations pages:
  - `http://localhost:3000/admin/projects`
  - `http://localhost:3000/admin/intake`
  - `http://localhost:3000/admin/duplicates`
  - `http://localhost:3000/admin/coverage`
  - `http://localhost:3000/admin/sources`

### Current Sprint Status

- Implemented:
  - deterministic PDF extraction v1 into staging only, with no direct canonical writes from parser output
  - parser run logs with status, candidate counts, warnings, errors, and diagnostics
  - source workspace extraction trigger plus parser-run visibility
  - anomaly checks for sold vs marketed, negative unsold, total vs marketed, unrealistic margin, missing latest cycle, location confidence downgrade, and chronology conflicts
  - admin ops and anomalies dashboards for ingestion health, backlog, coverage, location completeness, and parser health
- End-to-end manual flow for one report:
  - open `http://localhost:3000/admin/sources`
  - open or create a source report with a valid `source_url` or `source_file_path`
  - save the source metadata
  - run `Run automated extraction`
  - review parser-created candidates in the same source workspace or from `http://localhost:3000/admin/intake`
  - match, edit, publish, reject, or defer through the existing intake workflow
- Validation:
  - `python -m pytest apps/api/tests -q`
  - `npm run typecheck --workspace @real-estat-map/web`
  - `npm run build --workspace @real-estat-map/web`

### Coverage Expansion + Geocoding Hardening

- Implemented:
  - expanded company coverage registry fields for active status, latest registered/published/ingested report tracking, historical coverage range, and backfill status
  - new admin coverage pages:
    - `http://localhost:3000/admin/coverage`
    - `http://localhost:3000/admin/coverage/companies`
    - `http://localhost:3000/admin/coverage/reports`
    - `http://localhost:3000/admin/coverage/gaps`
  - new admin location review queue:
    - `http://localhost:3000/admin/projects/location-review`
  - field completeness tracking for key public project fields and CSV exports for gap review, missing location, missing metrics, and report coverage
  - hardened address/geocoding metadata with normalized display address, geocoding-ready flag, method, source label, and manual-vs-source geometry visibility
  - public/admin payload updates so location quality and manual/source-derived geometry are visible in project lists, project detail, and map panels
- Validation:
  - `python -m pytest apps/api/tests -q`
  - `python -m compileall apps/api`
  - `npm run typecheck --workspace @real-estat-map/web`
  - `npm run build --workspace @real-estat-map/web`
