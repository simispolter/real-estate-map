# API Contract — Public + Admin

חוזה API ראשוני לצוות Backend ו-Frontend. הניסוח כאן הוא פונקציונלי, לא OpenAPI מלא, אך מספיק כדי להתחיל פיתוח.

## עקרונות

- כל responses ב-JSON
- כל enums מוחזרים בצורה יציבה וקנונית
- pagination בכל רשימה
- filtering אחיד
- public API מופרד מ-admin API
- אין חשיפת מידע לא מאושר לציבור

## 1. Public API

## 1.1 GET /api/projects

### מטרה
להחזיר רשימת פרויקטים מסוננת.

### Query Params
- `q`
- `city`
- `neighborhood`
- `company_id`
- `project_business_type`
- `government_program_type`
- `project_urban_renewal_type`
- `project_status`
- `permit_status`
- `min_unsold_units`
- `max_unsold_units`
- `min_avg_price_per_sqm`
- `max_avg_price_per_sqm`
- `min_gross_margin_pct`
- `max_gross_margin_pct`
- `report_period`
- `sort_by`
- `sort_dir`
- `page`
- `page_size`

### Response Shape
```json
{
  "items": [
    {
      "project_id": "uuid",
      "canonical_name": "string",
      "company": {
        "id": "uuid",
        "name_he": "string"
      },
      "city": "string",
      "neighborhood": "string",
      "project_business_type": "regular_dev",
      "government_program_type": "none",
      "project_urban_renewal_type": "none",
      "project_status": "construction",
      "permit_status": "granted",
      "marketed_units": 120,
      "sold_units_cumulative": 80,
      "unsold_units": 40,
      "avg_price_per_sqm_cumulative": 28500,
      "gross_margin_expected_pct": 18.4,
      "latest_snapshot_date": "2025-12-31",
      "location_confidence": "street"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total": 340
  }
}
```

## 1.2 GET /api/projects/{projectId}

### מטרה
להחזיר פרטי פרויקט מלאים לפי latest published snapshot.

### Response Sections
- identity
- classification
- location
- latest_snapshot
- derived_metrics
- addresses
- source_quality

## 1.3 GET /api/projects/{projectId}/history

### מטרה
להחזיר את כל ה-snapshots לאורך זמן.

### Query Params
- `fields` — רשימת fields לבחירה
- `from`
- `to`

### Response
```json
{
  "project_id": "uuid",
  "snapshots": [
    {
      "snapshot_id": "uuid",
      "snapshot_date": "2025-03-31",
      "report_id": "uuid",
      "project_status": "marketing",
      "marketed_units": 100,
      "sold_units_cumulative": 52,
      "avg_price_per_sqm_cumulative": 27100,
      "gross_profit_unrecognized": 22000000
    }
  ]
}
```

## 1.4 GET /api/companies

### מטרה
להחזיר רשימת חברות.

### Response
- id
- name_he
- ticker
- active_status
- summary counts

## 1.5 GET /api/companies/{companyId}

### מטרה
להחזיר מסך חברה.

### Sections
- company metadata
- KPIs
- projects summary
- city distributions
- land reserves summary

## 1.6 GET /api/map/projects

### מטרה
להחזיר שכבת מפה לפי פילטרים.

### Query Params
זהים כמעט ל-`/api/projects`, בתוספת:
- `bbox`
- `zoom`
- `metric`

### Response Shape
```json
{
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [34.78, 32.07]
      },
      "properties": {
        "project_id": "uuid",
        "canonical_name": "string",
        "company_name": "string",
        "project_business_type": "urban_renewal",
        "project_status": "planning",
        "avg_price_per_sqm_cumulative": 31500,
        "unsold_units": 48,
        "location_confidence": "exact"
      }
    }
  ]
}
```

## 1.7 GET /api/filters/metadata

### מטרה
להחזיר values לפילטרים.

### Response
- companies
- cities
- neighborhoods
- enums
- min/max ranges

## 2. Admin API

כל נתיבי האדמין יהיו תחת `/api/admin` וידרשו auth + role.

## 2.1 POST /api/admin/reports/upload

### Body
multipart form-data
- file
- company_id
- report_type
- period_end_date
- publish_date

### Response
- report_id
- status

## 2.2 POST /api/admin/reports/{reportId}/parse

### מטרה
להריץ parser.

### Response
- ingestion_run_id
- status

## 2.3 GET /api/admin/reports/{reportId}/extraction-preview

### מטרה
להציג extraction artifacts.

### Response
- sections
- tables
- parse warnings
- raw text snippets

## 2.4 GET /api/admin/review-queue

### Query Params
- issue_type
- company_id
- status
- confidence_lt
- page
- page_size

### Response
- pending items
- issue summary

## 2.5 PATCH /api/admin/projects/{projectId}/classification

### Body
```json
{
  "project_business_type": "govt_program",
  "government_program_type": "mechir_lamishtaken",
  "project_urban_renewal_type": "none",
  "project_deal_type": "ownership",
  "project_usage_profile": "residential_only",
  "comment": "Override after review"
}
```

## 2.6 POST /api/admin/projects/{projectId}/addresses

### מטרה
להוסיף או לעדכן כתובות לפרויקט.

### Body
```json
{
  "addresses": [
    {
      "street": "הרצל",
      "house_number_from": 12,
      "house_number_to": 18,
      "city": "נתניה",
      "lat": 32.32,
      "lng": 34.85,
      "geometry_type": "line",
      "is_primary": true,
      "location_confidence": "street"
    }
  ],
  "comment": "Matched by admin"
}
```

## 2.7 POST /api/admin/projects/{projectId}/merge

### Body
```json
{
  "target_project_id": "uuid",
  "comment": "Same project under alternate naming"
}
```

## 2.8 POST /api/admin/projects/{projectId}/review

### Body
```json
{
  "review_type": "qa",
  "status": "approved",
  "comment": "Core fields verified"
}
```

## 2.9 POST /api/admin/publish

### Body
```json
{
  "report_ids": ["uuid"],
  "comment": "Publish reviewed Q4 reports"
}
```

## 2.10 POST /api/admin/publish/rollback

### Body
```json
{
  "publish_version": "2026-03-20T10:00:00Z",
  "comment": "Rollback due to merge error"
}
```

## 3. Error Model

### Standard Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid project_business_type",
    "details": {
      "field": "project_business_type"
    }
  }
}
```

### Common Codes
- UNAUTHORIZED
- FORBIDDEN
- VALIDATION_ERROR
- NOT_FOUND
- CONFLICT
- INGESTION_FAILED
- REVIEW_REQUIRED
- PUBLISH_BLOCKED

## 4. DTO Notes

- numeric fields מוחזרים כמספרים, לא strings
- null מותר כאשר field לא פורסם או לא זוהה
- derived fields יסומנו ב-meta אם צריך
- dates בפורמט ISO8601

## 5. Public Safety Rules

- public endpoints מחזירים רק `is_publicly_visible = true`
- entities עם review חסר יכולים להיות מוסתרים
- provenance מלא לעיתים ייחשף רק באדמין, ובציבור יוצג subset בלבד

## 6. Caching Strategy

### Cacheable
- filters metadata
- projects list queries
- company pages
- map layers by filter hash

### Not Cacheable Long
- admin review queue
- publish center
- ingestion run status

## 7. Versioning Strategy

- `/api/v1/...`
- breaking changes רק ב-v2
- response envelope עקבי לאורך כל ה-API
