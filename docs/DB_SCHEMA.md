# DB Schema — מערכת מודיעין פרויקטי מגורים

מסמך זה מגדיר את ישויות הדאטה, הקשרים ביניהן, שדות הליבה והעקרונות למסד נתונים רלציוני מבוסס PostgreSQL + PostGIS.

## 1. עקרונות סכימה

- snapshot-based model
- canonical project model
- normalized enums
- provenance לכל ערך חשוב
- multi-address support
- admin corrections without data loss
- soft delete + audit trail

## 2. תרשים ישויות ברמת על

```text
companies
  └─ reports
      └─ ingestion_runs

companies
  └─ project_masters
      ├─ project_aliases
      ├─ project_addresses
      ├─ project_snapshots
      │   ├─ project_sales_metrics
      │   ├─ project_financial_metrics
      │   ├─ project_planning_metrics
      │   ├─ project_sensitivity_items
      │   └─ field_provenance
      ├─ project_admin_reviews
      └─ project_merge_history

companies
  └─ land_reserves
```

## 3. טבלאות ליבה

## 3.1 companies

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| name_he | text | כן | שם עברי |
| name_en | text | לא | שם אנגלי |
| ticker | text | לא | סימול מסחר |
| public_status | text | כן | public / delisted / merged |
| sector | text | כן | residential_developer |
| created_at | timestamptz | כן | |
| updated_at | timestamptz | כן | |

### indexes
- unique(name_he)
- index(ticker)

## 3.2 reports

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| company_id | uuid | כן | FK companies |
| report_type | text | כן | annual / q1 / q2 / q3 / prospectus / presentation |
| period_type | text | כן | annual / quarterly / interim |
| period_start_date | date | לא | |
| period_end_date | date | כן | |
| publish_date | date | כן | |
| filing_reference | text | לא | מספר אסמכתה |
| source_file_path | text | כן | קובץ מקור |
| parser_version | text | כן | |
| checksum | text | לא | לזיהוי כפילויות |
| status | text | כן | uploaded / parsed / reviewed / published / failed |
| created_at | timestamptz | כן | |
| updated_at | timestamptz | כן | |

### indexes
- index(company_id, period_end_date desc)
- unique(company_id, report_type, period_end_date, publish_date)

## 3.3 ingestion_runs

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| report_id | uuid | כן | FK reports |
| started_at | timestamptz | כן | |
| finished_at | timestamptz | לא | |
| status | text | כן | running / success / failed / partial |
| summary_json | jsonb | לא | counters, errors |
| initiated_by | uuid | לא | user id |

## 3.4 project_masters

ישות קנונית של פרויקט.

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| company_id | uuid | כן | FK companies |
| canonical_name | text | כן | שם קנוני |
| city | text | לא | |
| neighborhood | text | לא | |
| district | text | לא | |
| asset_domain | text | כן | residential_only |
| project_business_type | text | כן | regular_dev / govt_program / urban_renewal |
| government_program_type | text | כן | none / mechir_lamishtaken / mechir_mטרה / dira_bahanaa / other |
| project_urban_renewal_type | text | כן | none / pinui_binui / tama_38_1 / tama_38_2 / other |
| project_deal_type | text | כן | ownership / combination / תמורות / jv / option / other |
| project_usage_profile | text | כן | residential_only / residential_commercial / residential_mixed |
| is_publicly_visible | boolean | כן | default true |
| location_confidence | text | כן | exact / street / neighborhood / city / unknown |
| classification_confidence | text | כן | high / medium / low |
| mapping_review_status | text | כן | pending / reviewed / approved / rejected |
| source_conflict_flag | boolean | כן | |
| notes_internal | text | לא | |
| created_at | timestamptz | כן | |
| updated_at | timestamptz | כן | |
| deleted_at | timestamptz | לא | soft delete |

### indexes
- index(company_id)
- index(city)
- index(neighborhood)
- index(project_business_type)
- gin(canonical_name gin_trgm_ops)

## 3.5 project_aliases

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| project_id | uuid | כן | FK project_masters |
| alias_name | text | כן | שם חלופי |
| alias_source | text | כן | report / admin / parser |
| first_seen_report_id | uuid | לא | |
| last_seen_report_id | uuid | לא | |
| created_at | timestamptz | כן | |

### indexes
- gin(alias_name gin_trgm_ops)
- unique(project_id, alias_name)

## 3.6 project_addresses

ריבוי כתובות לפרויקט אחד.

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| project_id | uuid | כן | FK project_masters |
| address_text_raw | text | לא | הטקסט כפי שחולץ |
| street | text | לא | |
| house_number_from | int | לא | |
| house_number_to | int | לא | |
| city | text | לא | |
| postal_code | text | לא | |
| lat | numeric(10,7) | לא | |
| lng | numeric(10,7) | לא | |
| geom | geometry | לא | point / line / polygon |
| geometry_type | text | כן | point / line / polygon / approximate_area |
| is_primary | boolean | כן | |
| location_confidence | text | כן | exact / street / neighborhood / city / unknown |
| source_type | text | כן | parser / admin / geocoder / imported |
| assigned_by | uuid | לא | |
| assigned_at | timestamptz | לא | |
| created_at | timestamptz | כן | |
| updated_at | timestamptz | כן | |

### indexes
- index(project_id)
- index(city, street)
- gist(geom)

## 3.7 project_snapshots

צילום פרויקט לפי דו"ח.

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| project_id | uuid | כן | FK project_masters |
| report_id | uuid | כן | FK reports |
| snapshot_date | date | כן | לרוב period_end_date |
| project_status | text | לא | planning / permit / construction / marketing / completed / stalled |
| permit_status | text | לא | none / pending / granted / partial |
| planning_status | text | לא | free text enum hybrid |
| signature_rate | numeric(5,2) | לא | אחוז |
| engineering_completion_rate | numeric(5,2) | לא | |
| financial_completion_rate | numeric(5,2) | לא | |
| total_units | int | לא | |
| marketed_units | int | לא | |
| sold_units_period | int | לא | |
| sold_units_cumulative | int | לא | |
| unsold_units | int | לא | נגזר או מדווח |
| sold_area_sqm_period | numeric(14,2) | לא | |
| sold_area_sqm_cumulative | numeric(14,2) | לא | |
| unsold_area_sqm | numeric(14,2) | לא | |
| avg_price_per_sqm_period | numeric(14,2) | לא | |
| avg_price_per_sqm_cumulative | numeric(14,2) | לא | |
| recognized_revenue_to_date | numeric(16,2) | לא | |
| expected_revenue_total | numeric(16,2) | לא | |
| expected_revenue_signed_contracts | numeric(16,2) | לא | |
| expected_revenue_unsold_inventory | numeric(16,2) | לא | |
| gross_profit_total_expected | numeric(16,2) | לא | |
| gross_profit_recognized | numeric(16,2) | לא | |
| gross_profit_unrecognized | numeric(16,2) | לא | |
| gross_margin_expected_pct | numeric(6,2) | לא | |
| expected_pre_tax_profit | numeric(16,2) | לא | |
| land_cost | numeric(16,2) | לא | |
| development_cost | numeric(16,2) | לא | |
| finance_cost_capitalized | numeric(16,2) | לא | |
| other_project_costs | numeric(16,2) | לא | |
| advances_received | numeric(16,2) | לא | |
| receivables_from_signed_contracts | numeric(16,2) | לא | |
| estimated_start_date | date | לא | |
| estimated_completion_date | date | לא | |
| needs_admin_review | boolean | כן | |
| created_at | timestamptz | כן | |
| updated_at | timestamptz | כן | |

### constraints
- unique(project_id, report_id)

### indexes
- index(project_id, snapshot_date desc)
- index(report_id)
- index(project_status)
- index(permit_status)

## 3.8 project_sales_metrics

טבלת הרחבה לשדות שיווק נוספים כשיש בדו"ח פירוט עשיר.

| שדה | סוג |
|---|---|
| id | uuid |
| snapshot_id | uuid |
| sales_rate_pct | numeric(5,2) |
| contracts_count | int |
| contract_backlog_value | numeric(16,2) |
| canceled_units_period | int |
| reservations_units | int |
| remarks | text |

## 3.9 project_financial_metrics

| שדה | סוג |
|---|---|
| id | uuid |
| snapshot_id | uuid |
| inventory_cost_unsold | numeric(16,2) |
| remaining_revenue | numeric(16,2) |
| remaining_gross_profit | numeric(16,2) |
| margin_remaining_pct | numeric(6,2) |
| project_roi_pct | numeric(6,2) |
| notes | text |

## 3.10 project_planning_metrics

| שדה | סוג |
|---|---|
| id | uuid |
| snapshot_id | uuid |
| signed_tenants_pct | numeric(5,2) |
| approved_units | int |
| planned_units | int |
| permit_units | int |
| planning_stage_text | text |
| planning_risk_flag | boolean |

## 3.11 land_reserves

ישות נפרדת כדי לא לערבב בין עתודת קרקע לפרויקט שיווקי.

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| company_id | uuid | כן | FK companies |
| related_project_id | uuid | לא | אם הוביל לפרויקט |
| reserve_name | text | כן | |
| city | text | לא | |
| neighborhood | text | לא | |
| reserve_status | text | כן | reserve / planning / suspended |
| planned_units | int | לא | |
| land_area_sqm | numeric(16,2) | לא | |
| deal_type | text | לא | |
| notes | text | לא | |
| is_publicly_visible | boolean | כן | |
| created_at | timestamptz | כן | |
| updated_at | timestamptz | כן | |

## 3.12 project_sensitivity_items

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| snapshot_id | uuid | כן | FK project_snapshots |
| sensitivity_type | text | כן | sale_price / construction_cost / finance_cost |
| delta_pct | numeric(6,2) | כן | |
| impact_value | numeric(16,2) | כן | |
| impact_metric | text | כן | revenue / profit / margin |

## 3.13 field_provenance

הטבלה הקריטית ביותר לאמינות המערכת.

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| entity_type | text | כן | project_master / snapshot / land_reserve / address |
| entity_id | uuid | כן | |
| field_name | text | כן | |
| raw_value | text | לא | הערך כפי שחולץ |
| normalized_value | text | לא | הערך לאחר נרמול |
| source_report_id | uuid | כן | FK reports |
| source_page | int | לא | |
| source_section | text | לא | |
| extraction_method | text | כן | table / text / rule / llm / admin |
| parser_version | text | לא | |
| confidence_score | numeric(5,2) | לא | |
| review_status | text | כן | pending / approved / corrected / rejected |
| reviewed_by | uuid | לא | |
| reviewed_at | timestamptz | לא | |
| created_at | timestamptz | כן | |

### indexes
- index(entity_type, entity_id)
- index(source_report_id)
- index(field_name)

## 3.14 project_admin_reviews

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| project_id | uuid | כן | |
| review_type | text | כן | location / classification / merge / qa |
| status | text | כן | pending / approved / rejected |
| payload_before | jsonb | לא | |
| payload_after | jsonb | לא | |
| comment | text | לא | |
| reviewer_id | uuid | לא | |
| reviewed_at | timestamptz | לא | |
| created_at | timestamptz | כן | |

## 3.15 project_merge_history

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| source_project_id | uuid | כן | project שנבלע |
| target_project_id | uuid | כן | project קנוני |
| reason | text | לא | |
| merged_by | uuid | לא | |
| merged_at | timestamptz | כן | |

## 3.16 users

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| email | text | כן | unique |
| full_name | text | לא | |
| role | text | כן | analyst / admin / super_admin |
| is_active | boolean | כן | |
| created_at | timestamptz | כן | |

## 3.17 audit_logs

| שדה | סוג | חובה | הערות |
|---|---|---:|---|
| id | uuid | כן | PK |
| actor_user_id | uuid | לא | |
| action | text | כן | |
| entity_type | text | כן | |
| entity_id | uuid | לא | |
| diff_json | jsonb | לא | |
| created_at | timestamptz | כן | |

## 4. enums מומלצים

מומלץ לייצג את הסיווגים גם כ-Postgres enums או lookup tables, לפי העדפת צוות הפיתוח.

### core enums
- report_type
- project_business_type
- government_program_type
- project_urban_renewal_type
- project_deal_type
- project_usage_profile
- location_confidence
- mapping_review_status
- permit_status
- project_status
- review_status
- user_role

## 5. קשרים עיקריים

- company 1:N reports
- company 1:N project_masters
- project_master 1:N project_aliases
- project_master 1:N project_addresses
- project_master 1:N project_snapshots
- report 1:N project_snapshots
- snapshot 1:N project_sensitivity_items
- snapshot 1:N field_provenance
- company 1:N land_reserves

## 6. derived views מומלצות

### vw_project_latest_snapshot
latest snapshot לכל פרויקט.

### vw_project_map_points
מכין דאטה יעיל למפה מתוך project + primary address + latest snapshot.

### vw_company_pipeline_summary
אגרגציות לפי חברה.

### vw_city_inventory_summary
אגרגציות לפי עיר.

## 7. כללי שלמות נתונים

- `project_masters.asset_domain` חייב להיות `residential_only` כדי להיות מוצג לציבור.
- `project_snapshots.report_id` חייב להתאים ל-company של הפרויקט.
- `project_addresses.is_primary` יחיד לכל פרויקט.
- אם `project_business_type != govt_program` אז `government_program_type = none`.
- אם `project_business_type != urban_renewal` אז `project_urban_renewal_type = none`.

## 8. partitioning והיקף עתידי

אם מספר ה-snapshots יגדל משמעותית, מומלץ לשקול partitioning של `project_snapshots` ו-`field_provenance` לפי שנה או לפי `report_id`.

## 9. migration strategy

- בסיס schema ב-SQL migrations
- seeding ל-enums
- backward-compatible migrations בלבד ב-production
- schema_version בטבלת metadata

## 10. metadata table

מומלץ להוסיף טבלת `system_metadata` עם:
- current_schema_version
- current_parser_version
- last_successful_publish_at
- maintenance_mode
