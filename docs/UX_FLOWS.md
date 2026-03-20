# UX Flows — מסכי מוצר, זרימות והרשאות

מסמך זה מתרגם את ה-PRD למסכים, מצבי מערכת וזרימות עיקריות. הוא נועד ל-Product, Design ו-Frontend.

## 1. עקרונות UX

- כניסה מהירה לערך, בלי להעמיס את המשתמש במפה ריקה
- חיפוש וסינון לפני exploration
- שקיפות לגבי איכות הנתונים
- distinction ברור בין public exploration לבין admin correction
- שמירה על מצב פילטרים ב-URL
- כל מסך צריך לעבוד טוב גם בלי map interaction

## 2. מפת מסכים

```text
Public
  Home/Search
    ├─ Project List
    ├─ Map View
    ├─ Project Page
    └─ Company Page

Admin
  Admin Dashboard
    ├─ Reports Queue
    ├─ Review Queue
    ├─ Project Review
    ├─ Location Assignment
    ├─ Merge & Aliases
    ├─ Classification Editor
    └─ Publish Center
```

## 3. Public Flow

## 3.1 Home / Search

### מטרת המסך
לתת כניסה אחת לכל המאגר.

### Layout
- אזור עליון: title + search bar
- אזור KPI: כרטיסי summary
- אזור פילטרים: toolbar אופקי + drawer מורחב
- אזור תוצאות: toggle בין List / Map / Company

### פילטרים ראשיים
- עיר
- שכונה
- חברה
- סוג פרויקט
- תת סוג
- סטטוס
- היתר
- שיעור שיווק
- יח"ד לא מכורות
- מחיר ממוצע למ"ר
- רווח גולמי
- תקופת דיווח

### states
- empty default
- filtered results
- no results
- loading
- partial data warning

### פעולות עיקריות
- חיפוש חופשי לפי שם פרויקט/חברה/אזור
- שמירת deep-link עם כל הפילטרים ב-URL
- מעבר ישיר למסך פרויקט
- מעבר למסך מפה עם אותם פילטרים

## 3.2 Map View

### מטרה
חקירה גיאוגרפית.

### Layout
- מפה במרכז
- panel צדדי עם filters ו-results
- legend דינמי לפי metric שנבחר
- mini cards לפרויקטים הנבחרים

### controls
- zoom / pan
- fit to results
- toggle clustering
- coloring metric selector
- basemap switch

### סוגי visual
- point
- line
- polygon
- approximate area badge

### badge חובה בכל פרויקט
- exact
- street
- neighborhood
- city
- unknown

### interaction
- hover על pin פותח tooltip
- click פותח side card
- click נוסף מוביל למסך פרויקט מלא

## 3.3 Project Page

### מבנה

#### A. Header
- שם פרויקט
- חברה
- עיר / שכונה
- badges: סוג פרויקט, תת סוג, סטטוס, ודאות מיקום
- last reported period

#### B. Executive Snapshot
- total units
- marketed units
- sold cumulative
- unsold units
- avg price per sqm
- expected revenue total
- expected gross profit

#### C. Classification Block
- מסלול: יזמי רגיל / ממשלתי / התחדשות
- תת סוג
- סוג עסקה
- פרופיל שימוש

#### D. Location Block
- כתובת ראשית
- כתובות נוספות
- מיקום על מפה קטנה
- רמת ודאות

#### E. Status & Planning
- project status
- permit status
- planning status
- signature rate
- completion rates
- start / completion dates

#### F. Sales & Inventory
- units sold period
- units sold cumulative
- unsold units
- sold sqm
- unsold sqm
- sales rate

#### G. Financials
- expected revenue
- recognized revenue
- unrecognized backlog
- expected gross profit
- recognized gross profit
- unrecognized gross profit
- expected margin

#### H. Trends
- גרף מחיר למ"ר
- גרף שיווק מצטבר
- גרף רווחיות
- compare snapshots toggle

#### I. Source & Provenance
- טבלת שדות עם מקור
- קישור לעמודים רלוונטיים
- אינדיקציה אם ערך תוקן ידנית

### states
- full data
- limited data
- conflicting data
- no precise location

## 3.4 Company Page

### מבנה
- header עם שם חברה
- KPI cards
- map of projects
- project table
- charts by city and business type
- inventory and margin summary
- land reserves section

### controls
- תקופת דיווח
- עיר
- סוג פרויקט
- sort by price / units / margin / unsold inventory

## 4. Admin Flow

## 4.1 Admin Dashboard

### widgets
- reports pending parse
- projects pending review
- conflicts pending resolution
- location assignments pending
- publish candidates

## 4.2 Reports Queue

### מטרה
לראות מצב ingest.

### table columns
- חברה
- קובץ
- תקופה
- parser version
- סטטוס
- שגיאות
- uploaded at
- actions

### actions
- parse
- re-run parse
- open extraction preview
- move to review

## 4.3 Review Queue

### table columns
- project name raw
- company
- issue type
- confidence
- suggested action
- assigned reviewer

### filters
- issue type
- company
- confidence
- report period

## 4.4 Project Review Screen

זהו מסך העבודה של האדמין.

### panels
- raw source preview
- normalized project data
- location editor
- classification editor
- aliases panel
- provenance panel
- audit panel

### issue types
- missing location
- low confidence classification
- possible duplicate
- source conflict
- missing public visibility decision

## 4.5 Location Assignment Flow

### כניסה
אדמין פותח פרויקט חסר מיקום.

### שלבים
1. רואה טקסט מקור ושם פרויקט.
2. רואה הצעות גיאוקידוד.
3. בוחר כתובת אחת או כמה כתובות.
4. יכול להוסיף טווח מספרי בית.
5. יכול להציב pin ידני על מפה.
6. קובע רמת ודאות.
7. שומר ומאשר.

### validation
- לפחות city או geometry
- אם יש יותר מכתובת אחת, אחת מסומנת כ-primary
- כל שינוי נרשם ב-audit log

## 4.6 Merge & Aliases Flow

### כניסה
המערכת זיהתה שייתכן ששני פרויקטים הם אותו פרויקט.

### תהליך
- מציגה similarity evidence
- מציגה source names, cities, addresses, snapshots
- האדמין בוחר merge או keep separate
- אם merge, בוחר target project canonical
- alias history נשמר
- snapshots מועברים ל-target בלי אובדן provenance

## 4.7 Classification Editor Flow

### editable fields
- project_business_type
- government_program_type
- project_urban_renewal_type
- project_deal_type
- project_usage_profile
- visibility to public

### rules
- התאמות enum תקינות בלבד
- שינוי דורש comment אם הוא override לערך parser

## 4.8 Publish Center

### מטרה
הפרדה בין reviewed data ל-published data.

### פעולות
- preview publish diff
- approve publish
- rollback to previous publish
- publish note

## 5. Role Permissions Matrix

| יכולת | Public | Admin | Super Admin |
|---|---:|---:|---:|
| צפייה במסך בית | כן | כן | כן |
| צפייה במסך מפה | כן | כן | כן |
| צפייה במסך פרויקט | כן | כן | כן |
| צפייה במסך חברה | כן | כן | כן |
| צפייה ב-provenance מלא | חלקי | כן | כן |
| שיוך מיקום | לא | כן | כן |
| תיקון סיווג | לא | כן | כן |
| merge projects | לא | כן | כן |
| publish reviewed data | לא | לא | כן |
| שינוי parser rules | לא | לא | כן |

## 6. UX Rules מחייבים

- מצב פילטרים תמיד ניתן לשיתוף דרך URL.
- מפה אינה הדרך היחידה לנווט; תמיד קיימת גם טבלה.
- אם data quality נמוך, מוצגת אזהרה גלויה.
- כל metric מוצג עם label ברור אם הוא מדווח, נגזר או מתוקן.
- לא מציגים false precision במפה.
- כל entity עם conflict_flag יקבל badge מתאים.

## 7. Empty / Error States

### Empty Search
"לא נמצאו פרויקטים בתנאים שבחרת"

### No Precise Location
"לפרויקט יש שיוך ברמת עיר בלבד"

### Partial Financial Data
"בחלק מהתקופות אין גילוי מלא של שדות הרווחיות"

### Admin Conflict
"קיים קונפליקט בין מקורות. נדרש review לפני פרסום"

## 8. Design Tokens עקרוניים

- טון רציני, מחקרי, לא צרכני-צבעוני
- צבע אזהרה נפרד ל-data quality
- צבע נפרד למסלול ממשלתי ולהתחדשות עירונית
- badges אחידים לכל enums
- טבלאות עם sticky headers ו-column chooser

## 9. Responsive Behavior

### Desktop
ברירת המחדל הראשית.

### Tablet
המפה נפתחת full width עם panel מתקפל.

### Mobile
לא יעד ראשוני ל-V1, אך מסך פרויקט צריך להיות קריא גם במובייל.

## 10. Analytics Events מומלצים

- search_submitted
- filter_changed
- project_opened
- company_opened
- map_pin_clicked
- compare_snapshots_used
- admin_location_saved
- admin_project_merged
- publish_completed
