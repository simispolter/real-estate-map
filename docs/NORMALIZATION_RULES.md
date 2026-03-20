# Normalization Rules — חילוץ, נרמול, שיוך ואיכות נתונים

המסמך מגדיר איך מעבירים נתונים מדו"ח PDF אל מודל קנוני אמין. זהו מסמך ליבה, כי בלי חוקים קשיחים המוצר יאבד אמינות.

## 1. שכבות נתונים

כל ערך עובר דרך ארבע שכבות:

1. **Source** — הטקסט או הטבלה המקוריים כפי שמופיעים בדו"ח
2. **Extracted** — הערך כפי שחולץ טכנית
3. **Normalized** — הערך שמופה לשדה קנוני
4. **Reviewed** — ערך שאושר או תוקן על ידי אדמין

אין דריסה של שכבה קודמת.

## 2. יחידת נרמול בסיסית

יחידת העבודה היא `field value with provenance`.

כלומר, לא רק "יש לפרויקט 120 יח"ד", אלא:
- entity
- field
- raw value
- normalized value
- source page
- source section
- extraction method
- confidence

## 3. שיוך פרויקט

### מטרת השיוך
להכריע אם שם שמופיע בדו"ח מייצג:
- פרויקט קיים
- alias של פרויקט קיים
- פרויקט חדש
- עתודת קרקע
- פרויקט לא רלוונטי לליבת המוצר

### אותות לזיהוי זהות פרויקט
- שם פרויקט
- חברה
- עיר
- שכונה
- כתובת
- מספר יח"ד
- סוג פרויקט
- מסלול ממשלתי / התחדשות
- דמיון לשמות קודמים

### חוקים
- אם שם דומה מאוד, עיר זהה ויח"ד בטווח דומה, מייצרים candidate alias
- אם שם זהה אך עיר שונה, לא מאחדים אוטומטית
- אם דו"ח מתאר "מתחם" ללא כתובת, לא ממציאים כתובת
- merge אוטומטי מותר רק ברמת confidence גבוהה מאוד, אחרת עובר לאדמין

## 4. שיוך מגורים בלבד

### כלל מחייב
רק רכיבי מגורים נכנסים ל-public product.

### חוקים
- אם פרויקט mixed-use, שומרים `project_usage_profile` מתאים
- אם רכיב המגורים אינו ניתן להפרדה במספרים, שומרים את הנתון אך מסמנים אותו כ-partial
- אם דו"ח מתאר מגזר שאינו מגורים, הוא לא נוצר כ-project master לציבור

## 5. סיווג סוג פרויקט

### project_business_type

#### regular_dev
פרויקט יזמי רגיל, ללא מסלול ממשלתי וללא התחדשות.

#### govt_program
כל פרויקט במסלול ממשלתי של שיווק דירות מוזלות.

#### urban_renewal
פרויקט פינוי בינוי, תמ"א או מסלול מקביל.

### כללי עדיפות
- אם קיים סימון מפורש של מחיר למשתכן / מחיר מטרה / דירה בהנחה, הסיווג הראשי הוא `govt_program`
- אם קיים סימון מפורש של פינוי בינוי / תמ"א, הסיווג הראשי הוא `urban_renewal`
- אם אין אינדיקציה, ברירת המחדל היא `regular_dev` אך confidence נמוך יותר

## 6. סיווג תת סוגים

### government_program_type
ממופה ממילים מפורשות בלבד או ממילון מונחים מאושר.

### project_urban_renewal_type
ממופה ממונחים מפורשים כמו:
- פינוי בינוי
- תמ"א 38/1
- תמ"א 38/2
- הריסה ובנייה
- חלופת שקד

אם יש רק "התחדשות עירונית" בלי פירוט, שומרים `urban_renewal` עם תת סוג `other` או `unknown_pending_review` לפי החלטת המימוש.

## 7. נרמול שדות כמותיים

### יח"ד
- כל unit count נשמר כמספר שלם
- אם מופיע טווח, נשמר raw value וה-normalized value נותר null עד review
- אם מצוין "כ-" או "בקירוב", מסמנים estimated flag

### סכומים כספיים
- נשמרים בערך מספרי אחיד
- מטבע נשמר בנפרד אם רלוונטי
- אם סכום מדווח באלפי ש"ח או במיליוני ש"ח, מנרמלים ליחידת בסיס אחידה
- raw formatting נשמר ב-provenance

### מחיר למ"ר
- נשמר כמספר בדיד לשטח עיקרי רלוונטי
- אם לא ברור אם מדובר ברוטו/נטו, מוסיפים field note ומורידים confidence

### אחוזים
- נשמרים במספר בין 0 ל-100
- לא שומרים גם `0.23` וגם `23%`; בוחרים פורמט אחיד

## 8. נרמול תאריכים

- כל date נשמר ב-ISO
- אם דווח רק חודש/שנה, נשמר raw value ו-normalized precision = partial
- estimated_start_date ו-estimated_completion_date מסומנים כ-estimated

## 9. מיקום וגיאוקידוד

### רמות ודאות
- exact
- street
- neighborhood
- city
- unknown

### חוקים
- exact ניתן רק אם קיימת כתובת מלאה או pin מאומת
- street ניתן אם יש רחוב בלי מספר או טווח כתובות
- neighborhood ניתן אם יש שכונה בלבד
- city ניתן אם רק העיר ידועה
- unknown כאשר גם עיר אינה ודאית

### גיאוקידוד
- geocoder מחזיר candidate list
- אין auto-accept למיקום exact בלי איכות מספקת
- admin override גובר על geocoder
- כל override נשמר עם source_type = admin

## 10. ריבוי כתובות

### מתי משתמשים
- שני בניינים שונים באותו פרויקט
- מתחם עם חזיתות מרובות
- פינוי בינוי על רצף כתובות

### חוקים
- לכל פרויקט יכולה להיות יותר מכתובת אחת
- רק כתובת אחת primary
- מותר לשמור טווח מספרי בית
- מותר לשמור approximate area כשהכתובות אינן חד משמעיות

## 11. conflict resolution

### סוגי קונפליקטים
- אותו שדה עם ערכים שונים בין דו"חות
- אותו שם פרויקט בשתי ערים
- נתון מגזרי לעומת נתון פרויקטלי
- שינוי חד מדי בין תקופות

### חוקים
- לא מוחקים ערך קודם
- latest report מקבל קדימות תצוגתית, לא מחיקתית
- אם אין הסבר ברור לשינוי חריג, מסמנים conflict_flag
- conflict בעל משמעות ציבורית עובר review לפני פרסום

## 12. confidence scoring

### מקורות confidence
- parse quality
- source clarity
- table structure quality
- presence of explicit labels
- consistency with previous snapshots
- admin confirmation

### threshold policy מוצעת
- 90–100 = high
- 70–89 = medium
- below 70 = low and requires review

## 13. שדות נגזרים

שדות נגזרים אינם מחליפים שדות מקור.

### rules
- נגזר נשמר בנפרד או מחושב ב-view
- כל field נגזר מקבל tag `derived=true`
- UI מציין אם metric הוא reported או derived

### דוגמאות
- unsold_units
- sales_rate_pct
- remaining_revenue
- remaining_gross_profit
- price_drift_pct
- margin_drift_pct

## 14. parser rule hierarchy

סדר קדימות מומלץ:

1. explicit table mapping
2. explicit section-specific regex/rules
3. cross-report reconciliation rules
4. LLM assisted extraction
5. admin review

אסור להשתמש ב-LLM כדי להמציא נתון חסר.

## 15. review policy

### review חובה כאשר
- location_confidence נמוך מ-street
- classification_confidence נמוך
- parser זיהה possible duplicate
- conflict_flag=true
- field critical missing: city, project type, major financial value, unit count

## 16. critical fields

המערכת לא מפרסמת project snapshot בלי מינימום fields מאושר:
- company
- canonical or provisional project name
- asset_domain
- project_business_type
- לפחות city או status מספקים
- report linkage

## 17. audit requirements

כל שינוי ידני חייב לכלול:
- מי שינה
- מתי שינה
- מה היה קודם
- מה הערך החדש
- reason/comment

## 18. anti-patterns שאסור לאפשר

- מיזוג אוטומטי אגרסיבי מדי של פרויקטים
- הצגת pin מדויק כשיש רק רמת עיר
- שמירת ערכים מנורמלים בלי raw source
- ערבוב בין נתוני מגורים לנתוני מסחר
- דריסה של snapshot קודם
