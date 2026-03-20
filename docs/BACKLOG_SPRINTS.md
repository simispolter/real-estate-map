# Backlog לפי ספרינטים — תוכנית בנייה לקודקס

המסמך מחלק את המוצר לספרינטים ישימים. הוא מניח צוות קטן עם Frontend, Backend ו-Data Engineering, וניתן לפרק ממנו משימות ישירות ל-Codex.

## הנחות עבודה

- אורך ספרינט: שבוע עד שבועיים
- יעד V1: תשתית מלאה + כמה חברות ראשונות ב-staging
- strategy: vertical slices סביב ישויות הליבה

## Sprint 0 — Project Foundation

### מטרות
- להקים שלד monorepo
- לנעול conventions
- להרים סביבת פיתוח ראשונית

### משימות
- יצירת monorepo עם apps/services/packages
- בחירת stack סופית
- הקמת lint, format, typecheck, CI
- יצירת README ותיקיית docs
- הגדרת env management
- הקמת Postgres + PostGIS מקומית
- הגדרת auth בסיסי לאדמין

### deliverables
- repo runnable
- db container עולה
- web + admin + api skeleton
- docs committed

## Sprint 1 — Database & Shared Types

### מטרות
- להטמיע את סכמת הדאטה
- לייצר shared enums/types

### משימות Backend
- כתיבת migrations לכל טבלאות הליבה
- seed ל-enums
- metadata tables
- audit log infra

### משימות Shared
- shared type package ל-enums ו-DTOs
- validation schemas

### deliverables
- schema migration מלאה
- ERD מעודכן
- generated types

## Sprint 2 — Report Intake & Storage

### מטרות
- לקלוט קבצי דו"ח ולנהל ingestion runs

### משימות
- upload endpoint לקבצי דו"ח
- object storage adapter
- reports table wiring
- ingestion_runs lifecycle
- status transitions
- admin reports queue screen בסיסי

### deliverables
- דו"ח עולה למערכת
- נרשם run
- admin רואה תור דו"חות

## Sprint 3 — Extraction Pipeline v1

### מטרות
- לחלץ טקסט, טבלאות וסקשנים ראשונים

### משימות Data
- PDF text extraction service
- table extraction service
- section detector
- parser interface
- raw extraction artifact storage

### משימות Admin
- extraction preview screen
- error states

### deliverables
- ניתן לראות raw extraction לכל דו"ח
- parser hooks פעילים

## Sprint 4 — Canonical Project Resolution

### מטרות
- ליצור project_masters, aliases ו-snapshots ראשונים

### משימות
- project identity resolver
- alias matching rules
- project create/update pipeline
- snapshot creation per report
- field provenance write path

### deliverables
- פרויקטים קנוניים נוצרים אוטומטית
- snapshots נשמרים
- provenance נשמר לכל שדה ליבה

## Sprint 5 — Admin Review Core

### מטרות
- לאפשר review בסיסי לפני פרסום

### משימות Frontend/Admin
- review queue
- project review screen
- provenance panel
- review actions

### משימות Backend
- review status transitions
- admin review endpoints
- audit log integration

### deliverables
- אדמין יכול לאשר/לדחות שדות ופרויקטים
- review workflow פעיל

## Sprint 6 — Location Assignment Module

### מטרות
- לבנות את מודול המיקום שהוא ליבת האיכות

### משימות
- geocoding adapter
- project_addresses CRUD
- primary address rules
- map picker in admin
- multi-address UI
- confidence assignment

### deliverables
- אדמין יכול לשייך כתובת אחת או כמה כתובות לפרויקט
- ניתן להציב pin ידני
- location confidence נשמר

## Sprint 7 — Classification & Merge Module

### מטרות
- לאפשר תיקון סיווגים ואיחוד פרויקטים

### משימות
- classification editor
- merge suggestions service
- merge workflow + history
- alias history panel
- validation rules בין enums

### deliverables
- אדמין משנה סוג פרויקט וסוג עסקה
- אפשר למזג פרויקטים בלי לאבד snapshots

## Sprint 8 — Public API v1

### מטרות
- לחשוף נתונים לממשק הציבורי

### משימות
- GET /projects
- GET /projects/:id
- GET /projects/:id/history
- GET /companies
- GET /companies/:id
- GET /map/projects
- GET /filters/metadata
- query optimization + indexes

### deliverables
- API ציבורי ראשוני עובד עם pagination, filtering, sorting

## Sprint 9 — Home Screen & Project Table

### מטרות
- להעמיד חוויית חיפוש שימושית גם בלי המפה

### משימות Frontend
- home search layout
- KPI cards
- filters toolbar
- projects table
- URL state sync
- loading, empty and error states

### deliverables
- מסך בית שימושי עם טבלת פרויקטים ופילטרים מלאים

## Sprint 10 — Mapbox Experience

### מטרות
- לחבר את הדאטה למפה

### משימות
- map layer model
- clustering
- project pins/cards
- coloring metrics
- fit-to-results
- map/list sync
- location confidence badges

### deliverables
- מפת פרויקטים פעילה עם filters

## Sprint 11 — Project Page

### מטרות
- לבנות את מסך הערך המרכזי של המוצר

### משימות
- header + badges
- executive snapshot cards
- classification block
- location block
- status block
- sales/inventory block
- financials block
- trend charts
- provenance table

### deliverables
- מסך פרויקט מלא עם היסטוריית snapshots

## Sprint 12 — Company Page

### מטרות
- להציג פייפליין מגורים ברמת חברה

### משימות
- company summary endpoint enrichments
- map by company
- company projects table
- city distribution charts
- inventory and margin summary
- land reserves section

### deliverables
- מסך חברה מלא

## Sprint 13 — Derived Metrics & Quality Flags

### מטרות
- לשדרג את המוצר מכלי תצוגה לכלי מודיעין

### משימות
- calculate unsold units
- calculate sales rate
- price drift
- margin drift
- permit risk flag
- planning stagnation flag
- conflict badges in UI

### deliverables
- metrics נגזרים זמינים ב-API ובמסכים

## Sprint 14 — Publish Workflow & Versioning

### מטרות
- להפריד staging data מ-published data

### משימות
- publish center
- publish diff preview
- rollback mechanism
- version tagging
- release notes field

### deliverables
- publish controlled workflow

## Sprint 15 — Hardening & Staging Launch

### מטרות
- לייצב, לבדוק ולהעלות staging usable

### משימות
- performance optimization
- security review
- seed demo dataset
- QA checklist
- observability and logs
- backup strategy
- smoke tests

### deliverables
- staging environment usable end to end

## Parallel Workstreams

## A. Data Parsing Workstream
- parser templates per company
- normalization rules
- confidence scoring
- extraction QA

## B. Design System Workstream
- badges
- tables
- cards
- metric formatting
- admin form patterns

## C. DevOps Workstream
- environments
- secrets
- db backups
- deployment pipelines

## Suggested Codex Task Breakdown

כל ספרינט ניתן לפירוק למשימות Codex בפורמט הבא:

### Task Template
- Context
- Goal
- Files to touch
- Acceptance criteria
- Non-goals
- Test plan

### Example
**Task:** Build project_addresses CRUD with primary-address validation  
**Acceptance criteria:**
- project can have multiple addresses
- exactly zero or one primary address
- address update writes audit log
- API rejects invalid confidence enum

## Must-have Acceptance Criteria Across Sprints

- כל endpoint עם validation מלא
- כל שינוי אדמין יוצר audit log
- כל ערך מרכזי נשמר עם provenance
- public API לא מחזיר entities שאינם `is_publicly_visible`
- map API לא מחזיר false precision

## Cut List אם צריך להדק V1

אם צריך לקצר זמן, הדברים האחרונים שצריך לדחות, לא הראשונים:
- compare mode בין חברות
- export Excel
- advanced charts
- automated merge suggestions מתקדמים
- publish notes מפורטים

הדברים שאסור לדחות:
- schema מלא
- provenance
- admin review
- location assignment
- classification editor
- project page
