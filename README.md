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

### Service URLs

- Web: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
