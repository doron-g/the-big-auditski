from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

SUSPICIOUS_ALTS = {
    "image", "img", "photo", "pic", "picture", "logo", "icon", "untitled",
    "banner", "poster", "flyer", "placeholder", "design",
    "תמונה", "צילום", "לוגו", "אייקון", "תמונת נושא", "כרזה", "פוסטר", "באנר",
    "עיצוב ללא שם", "עיצוב", "אירוע", "מלון"
}

EVENT_KEYWORDS = [
    "עיצוב-ללא-שם", "עיצוב", "event", "poster", "flyer", "invitation", "banner",
    "agenda", "mudaa", "kenes", "hefresh", "mivtza", "deal", "hotel", "package",
    "nofesh", "tarbut", "mofa", "harzaa", "seminar", "workshop", "sale", "promo",
    "ad_", "ad-", "לוז", "מודעה", "אירוע", "כנס", "הזמנה", "מבצע", "חבילה", "נופש",
    "מלון", "הופעה", "שבת", "נופשים", "סופש"
]

VAGUE_LINK_WORDS = [
    "לחץ כאן", "לחצי כאן", "הקלק כאן", "קרא עוד", "למידע נוסף",
    "לפרטים נוספים", "פרטים נוספים", "לפרטים", "לחץ", "קרא", "עוד",
    "click here", "read more", "more", "learn more", "details"
]

def audit_accessibility(soup: BeautifulSoup) -> dict:
    issues = []
    compliance_checks = []
    
    # -------------------------------------------------------------
    # 1. HTML lang & dir attribute (WCAG 3.1.1 - Level A & ת"י 5568)
    # -------------------------------------------------------------
    html_tag = soup.find("html")
    lang = html_tag.get("lang", "").strip() if html_tag else ""
    dir_attr = html_tag.get("dir", "").strip() if html_tag else ""
    
    if lang:
        compliance_checks.append({
            "id": "wcag_lang",
            "name": "הגדרת שפת מסמך ראשית",
            "standard": "WCAG 3.1.1 (Level A) & ת\"י 5568",
            "status": "passed",
            "details": f"שפת הדף הראשית מוגדרת כראוי בתגית <html>: '{lang}' (כיוון טקסט: '{dir_attr or 'ברירת מחדל'}'). קוראי מסך יקראו את הטקסט בהגייה נכונה."
        })
    else:
        issues.append({
            "type": "missing_html_lang",
            "severity": "critical",
            "message": "חסר מאפיין lang בתגית <html> (למשל: <html lang='he' dir='rtl'>)",
            "element": "<html>",
            "recommendation": "הגדר תמיד את שפת הדף הראשית בתגית <html> כדי שקוראי מסך יקראו את הטקסט בהגייה נכונה."
        })
        compliance_checks.append({
            "id": "wcag_lang",
            "name": "הגדרת שפת מסמך ראשית",
            "standard": "WCAG 3.1.1 (Level A) & ת\"י 5568",
            "status": "failed",
            "details": "לא הוגדר מאפיין lang בתגית <html>. קורא מסך עלול לקרוא את הטקסט בג'יבריש ובמבטא שגוי."
        })
        
    # -------------------------------------------------------------
    # 2. Heading hierarchy audit (WCAG 1.3.1 & 2.4.6)
    # -------------------------------------------------------------
    headings = soup.find_all(re.compile(r"^h[1-6]$"))
    heading_tree = []
    h1_count = 0
    prev_level = 0
    has_heading_skips = False
    has_empty_headings = False
    
    for h in headings:
        level = int(h.name[1])
        text = h.get_text(strip=True)
        heading_tree.append({
            "tag": h.name,
            "level": level,
            "text": text[:80] + ("..." if len(text) > 80 else "")
        })
        
        if level == 1:
            h1_count += 1
            
        if not text:
            has_empty_headings = True
            issues.append({
                "type": "empty_heading",
                "severity": "medium",
                "message": f"נמצאה כותרת ריקה מתגית <{h.name}>",
                "element": str(h)[:100],
                "recommendation": "מחק כותרות ריקות או הוסף להן תוכן ברור לקוראי מסך."
            })
            
        if prev_level > 0 and level > prev_level + 1:
            has_heading_skips = True
            issues.append({
                "type": "heading_level_skipped",
                "severity": "medium",
                "message": f"דילוג בהיררכיית כותרות: מעבר מ-<h{prev_level}> ישירות ל-<h{level}>",
                "element": f"<{h.name}>{text[:40]}</{h.name}>",
                "recommendation": f"אל תדלג על רמות כותרת. השתמש ב-<h{prev_level + 1}> במקום <h{level}> לשמירה על סדר לוגי."
            })
        prev_level = level
        
    if h1_count == 1:
        compliance_checks.append({
            "id": "wcag_h1",
            "name": "כותרת ראשית <h1> יחידה",
            "standard": "WCAG 1.3.1 & 2.4.6 & ת\"י 5568",
            "status": "passed",
            "details": "קיימת כותרת <h1> ראשית אחת ויחידה המגדירה בצורה ברורה את נושא הדף."
        })
    elif h1_count == 0:
        issues.append({
            "type": "missing_h1",
            "severity": "critical",
            "message": "לא נמצאה כותרת ראשית <h1> בדף",
            "element": "<body>",
            "recommendation": "הוסף כותרת <h1> אחת ויחידה המגדירה את הנושא הראשי של הדף. קריטי ל-SEO ולנגישות."
        })
        compliance_checks.append({
            "id": "wcag_h1",
            "name": "כותרת ראשית <h1> יחידה",
            "standard": "WCAG 1.3.1 & 2.4.6 & ת\"י 5568",
            "status": "failed",
            "details": "לא נמצאה כותרת <h1> בדף. משתמשי קורא מסך אינם יכולים לאתר את נושא הדף בקלות."
        })
    else:
        issues.append({
            "type": "multiple_h1",
            "severity": "warning",
            "message": f"נמצאו {h1_count} כותרות <h1> בדף (מומלץ כותרת H1 אחת לכל דף)",
            "element": "<h1>",
            "recommendation": "השאר רק כותרת <h1> ראשית אחת, ושנה את שאר הכותרות ל-<h2> ומטה."
        })
        compliance_checks.append({
            "id": "wcag_h1",
            "name": "כותרת ראשית <h1> יחידה",
            "standard": "WCAG 1.3.1 & 2.4.6 & ת\"י 5568",
            "status": "failed",
            "details": f"נמצאו {h1_count} כותרות H1 בדף במקום כותרת ראשית אחת. מומלץ לאחד לרמה אחת."
        })

    if len(headings) > 0 and not has_heading_skips and not has_empty_headings:
        compliance_checks.append({
            "id": "wcag_headings_order",
            "name": "היררכיה וסדר כותרות לוגי",
            "standard": "WCAG 1.3.1 (Info and Relationships)",
            "status": "passed",
            "details": f"נבדקו {len(headings)} כותרות בדף, סדר הכותרות עקבי, מדורג נכון וללא דילוגים או כותרות ריקות."
        })
    elif len(headings) > 0:
        compliance_checks.append({
            "id": "wcag_headings_order",
            "name": "היררכיה וסדר כותרות לוגי",
            "standard": "WCAG 1.3.1 (Info and Relationships)",
            "status": "failed",
            "details": "נמצאו דילוגים בין רמות כותרת או כותרות ריקות הפוגעות ברצף הניווט לקוראי מסך."
        })
    else:
        compliance_checks.append({
            "id": "wcag_headings_order",
            "name": "היררכיה וסדר כותרות לוגי",
            "standard": "WCAG 1.3.1 (Info and Relationships)",
            "status": "passed",
            "details": "לא נמצאו כותרות בדף הדורשות בדיקת היררכיה."
        })

    # -------------------------------------------------------------
    # 3. Form fields accessibility (WCAG 1.3.1 & 3.3.2)
    # -------------------------------------------------------------
    form_inputs = soup.find_all(["input", "textarea", "select"])
    interactive_inputs = 0
    unlabeled_inputs = 0
    
    for inp in form_inputs:
        inp_type = inp.get("type", "text").lower()
        if inp_type in ["hidden", "submit", "button", "reset", "image"]:
            continue
            
        interactive_inputs += 1
        inp_id = inp.get("id", "")
        aria_label = inp.get("aria-label", "")
        aria_labelledby = inp.get("aria-labelledby", "")
        title = inp.get("title", "")
        
        has_label = False
        if inp_id:
            label = soup.find("label", attrs={"for": inp_id})
            if label and label.get_text(strip=True):
                has_label = True
                
        if not has_label:
            parent_label = inp.find_parent("label")
            if parent_label and parent_label.get_text(strip=True):
                has_label = True
                
        if not has_label and not aria_label and not aria_labelledby and not title:
            unlabeled_inputs += 1
            issues.append({
                "type": "missing_form_label",
                "severity": "high",
                "message": f"שדה טופס מסוג '{inp_type}' ללא תווית <label> או aria-label",
                "element": str(inp)[:120],
                "recommendation": "הוסף תגית <label for='...'> מקושרת ל-id של השדה, או הוסף מאפיין aria-label. placeholder אינו תחליף לתווית."
            })
            
    if interactive_inputs > 0 and unlabeled_inputs == 0:
        compliance_checks.append({
            "id": "wcag_form_labels",
            "name": "תוויות נגישות לשדות טופס (<label>)",
            "standard": "WCAG 1.3.1 & 3.3.2 & ת\"י 5568",
            "status": "passed",
            "details": f"כל {interactive_inputs} שדות הקלט בטפסים מקושרים כראוי לתוויות נגישות (<label>) או ל-aria-label."
        })
    elif interactive_inputs > 0:
        compliance_checks.append({
            "id": "wcag_form_labels",
            "name": "תוויות נגישות לשדות טופס (<label>)",
            "standard": "WCAG 1.3.1 & 3.3.2 & ת\"י 5568",
            "status": "failed",
            "details": f"נמצאו {unlabeled_inputs} מתוך {interactive_inputs} שדות קלט ללא תווית מקושרת (למשתמש עיוור לא ברור מה להקליד)."
        })
    else:
        compliance_checks.append({
            "id": "wcag_form_labels",
            "name": "תוויות נגישות לשדות טופס (<label>)",
            "standard": "WCAG 1.3.1 & 3.3.2 & ת\"י 5568",
            "status": "passed",
            "details": "לא נמצאו שדות קלט או טפסים בדף זה הדורשים תוויות."
        })

    # -------------------------------------------------------------
    # 4. Buttons with accessible name (WCAG 4.1.2)
    # -------------------------------------------------------------
    buttons = soup.find_all("button")
    unnamed_buttons = 0
    for btn in buttons:
        text = btn.get_text(strip=True)
        aria_label = btn.get("aria-label", "")
        title = btn.get("title", "")
        img_alt = ""
        btn_img = btn.find("img")
        if btn_img:
            img_alt = btn_img.get("alt", "")
            
        if not text and not aria_label and not title and not img_alt:
            unnamed_buttons += 1
            issues.append({
                "type": "empty_button",
                "severity": "high",
                "message": "כפתור ללא טקסט או תווית נגישה (aria-label). נפוץ בכפתורי אייקון",
                "element": str(btn)[:120],
                "recommendation": "הוסף מאפיין aria-label='תיאור הפעולה' (למשל: סגור, חפש, פתח תפריט)."
            })
            
    if len(buttons) > 0 and unnamed_buttons == 0:
        compliance_checks.append({
            "id": "wcag_buttons_name",
            "name": "שמות ותוויות נגישות לכפתורים",
            "standard": "WCAG 4.1.2 (Name, Role, Value)",
            "status": "passed",
            "details": f"כל {len(buttons)} הכפתורים בדף כוללים טקסט גלוי או תווית נגישה (aria-label)."
        })
    elif len(buttons) > 0:
        compliance_checks.append({
            "id": "wcag_buttons_name",
            "name": "שמות ותוויות נגישות לכפתורים",
            "standard": "WCAG 4.1.2 (Name, Role, Value)",
            "status": "failed",
            "details": f"נמצאו {unnamed_buttons} כפתורים ללא שם נגיש או טקסט (למשל כפתורי אייקון ללא aria-label)."
        })
    else:
        compliance_checks.append({
            "id": "wcag_buttons_name",
            "name": "שמות ותוויות נגישות לכפתורים",
            "standard": "WCAG 4.1.2 (Name, Role, Value)",
            "status": "passed",
            "details": "לא נמצאו כפתורי <button> בדף."
        })

    # -------------------------------------------------------------
    # 5. Semantic Landmarks (WCAG 2.4.1)
    # -------------------------------------------------------------
    has_main = bool(soup.find("main") or soup.find(attrs={"role": "main"}))
    has_header = bool(soup.find("header") or soup.find(attrs={"role": "banner"}))
    has_footer = bool(soup.find("footer") or soup.find(attrs={"role": "contentinfo"}))
    has_nav = bool(soup.find("nav") or soup.find(attrs={"role": "navigation"}))
    
    if has_main:
        compliance_checks.append({
            "id": "wcag_main_landmark",
            "name": "אזור תוכן מרכזי סמנטי (<main>)",
            "standard": "WCAG 2.4.1 (Bypass Blocks)",
            "status": "passed",
            "details": "קיים אזור <main> תקני המאפשר למשתמשי מקלדת וקוראי מסך לדלג ישירות לתוכן העיקרי."
        })
    else:
        issues.append({
            "type": "missing_main_landmark",
            "severity": "medium",
            "message": "חסר אזור תוכן ראשי סמנטי (<main>)",
            "element": "<body>",
            "recommendation": "עטוף את התוכן המרכזי של הדף בתגית <main> כדי לאפשר למשתמשי מקלדת וקוראי מסך לדלג ישירות לתוכן."
        })
        compliance_checks.append({
            "id": "wcag_main_landmark",
            "name": "אזור תוכן מרכזי סמנטי (<main>)",
            "standard": "WCAG 2.4.1 (Bypass Blocks)",
            "status": "failed",
            "details": "חסר אזור סמנטי ראשי <main>. משתמשי מקלדת נאלצים לנווט דרך כל תפריטי האתר בכל מעבר דף."
        })

    # -------------------------------------------------------------
    # 6. Zoom restriction in viewport (WCAG 1.4.4)
    # -------------------------------------------------------------
    viewport = soup.find("meta", attrs={"name": "viewport"})
    zoom_blocked = False
    if viewport:
        content = viewport.get("content", "").lower()
        if "user-scalable=no" in content or "user-scalable=0" in content or "maximum-scale=1" in content:
            zoom_blocked = True
            issues.append({
                "type": "zoom_disabled",
                "severity": "critical",
                "message": "זום מבוטל בתגית ה-viewport (user-scalable=no או maximum-scale=1). מונע הגדלת טקסט!",
                "element": str(viewport)[:100],
                "recommendation": "הסר את user-scalable=no ו-maximum-scale=1 מתגית ה-viewport כדי לאפשר למשתמשי מובייל לבצע זום כנדרש בתקן נגישות."
            })
            compliance_checks.append({
                "id": "wcag_zoom_enabled",
                "name": "אפשרות הגדלת טקסט וזום במובייל",
                "standard": "WCAG 1.4.4 (Resize Text - Level AA)",
                "status": "failed",
                "details": "הזום במובייל נחסם באמצעות user-scalable=no או maximum-scale=1, בניגוד לחוק ולתקן."
            })
            
    if not zoom_blocked:
        compliance_checks.append({
            "id": "wcag_zoom_enabled",
            "name": "אפשרות הגדלת טקסט וזום במובייל",
            "standard": "WCAG 1.4.4 (Resize Text - Level AA)",
            "status": "passed",
            "details": "הגדלת תצוגה וזום במכשירים ניידים מאופשרת ותואמת לתקן (ללא חסימת משתמש כבד ראייה)."
        })

    # -------------------------------------------------------------
    # 7. Tables without headers (WCAG 1.3.1)
    # -------------------------------------------------------------
    tables = soup.find_all("table")
    bad_tables = 0
    for tbl in tables:
        if not tbl.find("th"):
            bad_tables += 1
            issues.append({
                "type": "table_without_headers",
                "severity": "medium",
                "message": "טבלת נתונים ללא כותרות עמודה (<th>)",
                "element": str(tbl)[:100],
                "recommendation": "הוסף תגיות <th> לראש הטבלה כדי שמשתמשי קורא מסך יוכלו להבין את משמעות הנתונים בכל תא."
            })
            
    if len(tables) > 0 and bad_tables == 0:
        compliance_checks.append({
            "id": "wcag_tables",
            "name": "כותרות עמודה בטבלאות נתונים (<th>)",
            "standard": "WCAG 1.3.1 (Info and Relationships)",
            "status": "passed",
            "details": f"כל {len(tables)} הטבלאות בדף כוללות כותרות עמודה מוגדרות (<th>) לקריאה מסודרת."
        })
    elif len(tables) > 0:
        compliance_checks.append({
            "id": "wcag_tables",
            "name": "כותרות עמודה בטבלאות נתונים (<th>)",
            "standard": "WCAG 1.3.1 (Info and Relationships)",
            "status": "failed",
            "details": f"נמצאו {bad_tables} טבלאות נתונים ללא כותרות <th>. קורא מסך אינו יכול להקריא הקשר לעמודות."
        })
    else:
        compliance_checks.append({
            "id": "wcag_tables",
            "name": "כותרות עמודה בטבלאות נתונים (<th>)",
            "standard": "WCAG 1.3.1 (Info and Relationships)",
            "status": "passed",
            "details": "לא נמצאו טבלאות נתונים בדף."
        })

    # -------------------------------------------------------------
    # 8. STRICT: Images with Alt Attributes (WCAG 1.1.1 & ת"י 5568)
    # Checks missing alt, empty alt on content images, and placeholder/suspicious alts
    # -------------------------------------------------------------
    imgs = soup.find_all("img")
    missing_alt_imgs = []
    empty_alt_content_imgs = []
    poor_alt_imgs = []
    
    for img in imgs:
        src = img.get("src") or img.get("data-src") or ""
        alt = img.get("alt")
        role = img.get("role", "")
        aria_hidden = img.get("aria-hidden", "") == "true"
        is_explicitly_decorative = role in ["presentation", "none"] or aria_hidden
        
        # 1. Missing alt attribute completely
        if alt is None:
            missing_alt_imgs.append(img)
            continue
            
        alt_stripped = alt.strip()
        
        # 2. Empty alt on content images
        # An image is considered content if inside link, inside card/article, or has informative dimensions/path, and NOT explicitly decorative
        if alt_stripped == "":
            is_in_link = bool(img.find_parent("a"))
            is_in_card = bool(img.find_parent(lambda t: t.name in ["article", "li", "figure"] or any(c in str(t.get("class", [])) for c in ["card", "item", "hotel", "deal", "post"])))
            is_large = False
            w, h = img.get("width"), img.get("height")
            if (w and str(w).isdigit() and int(w) > 80) or (h and str(h).isdigit() and int(h) > 80):
                is_large = True
                
            fname = src.split("/")[-1].lower() if "/" in src else src.lower()
            is_content_name = any(k in fname for k in EVENT_KEYWORDS)
            
            if not is_explicitly_decorative and (is_in_link or is_in_card or is_large or is_content_name):
                empty_alt_content_imgs.append(img)
            continue
            
        # 3. Suspicious / placeholder alt
        alt_clean = alt_stripped.lower()
        if alt_clean in SUSPICIOUS_ALTS or alt_clean.endswith((".jpg", ".png", ".webp", ".jpeg", ".svg", ".gif")):
            poor_alt_imgs.append(img)
        elif len(alt_stripped) < 3 and not alt_stripped.isalnum():
            poor_alt_imgs.append(img)

    total_alt_failures = len(missing_alt_imgs) + len(empty_alt_content_imgs) + len(poor_alt_imgs)
    
    if len(imgs) == 0:
        compliance_checks.append({
            "id": "wcag_img_alt",
            "name": "טקסט חלופי לתמונות תוכן (Alt Text)",
            "standard": "WCAG 1.1.1 (Non-text Content) & ת\"י 5568",
            "status": "passed",
            "details": "לא נמצאו תמונות בדף."
        })
    elif total_alt_failures == 0:
        compliance_checks.append({
            "id": "wcag_img_alt",
            "name": "טקסט חלופי לתמונות תוכן (Alt Text)",
            "standard": "WCAG 1.1.1 (Non-text Content) & ת\"י 5568",
            "status": "passed",
            "details": f"כל {len(imgs)} התמונות בדף כוללות תיאור חלופי (Alt) תקין וממצה, ללא טקסט סתמי וללא התעלמות מתמונות תוכן."
        })
    else:
        sample_faults = []
        if missing_alt_imgs:
            sample_faults.append(f"{len(missing_alt_imgs)} ללא תגית alt כלל")
        if empty_alt_content_imgs:
            sample_faults.append(f"{len(empty_alt_content_imgs)} תמונות תוכן/כרטיסים עם alt ריק")
        if poor_alt_imgs:
            sample_faults.append(f"{len(poor_alt_imgs)} עם alt סתמי/שם קובץ")
            
        compliance_checks.append({
            "id": "wcag_img_alt",
            "name": "טקסט חלופי לתמונות תוכן (Alt Text)",
            "standard": "WCAG 1.1.1 (Non-text Content) & ת\"י 5568",
            "status": "failed",
            "details": f"נמצאו {total_alt_failures} תמונות עם ליקויי נגישות ב-Alt ({', '.join(sample_faults)}). משתמשי קוראי מסך מפספסים מידע חיוני."
        })
        
        if missing_alt_imgs:
            issues.append({
                "type": "missing_alt",
                "severity": "high",
                "message": f"נמצאו {len(missing_alt_imgs)} תמונות ללא מאפיין alt כלל",
                "element": str(missing_alt_imgs[0])[:120],
                "recommendation": "הוסף מאפיין alt='תיאור התמונה' לכל תמונת תוכן, או alt='' ו-role='presentation' רק לתמונות קישוט."
            })
            
        if empty_alt_content_imgs:
            issues.append({
                "type": "empty_alt_content_image",
                "severity": "high",
                "message": f"נמצאו {len(empty_alt_content_imgs)} תמונות תוכן/כרטיסים עם מאפיין alt ריק (אינן דקורטיביות!)",
                "element": str(empty_alt_content_imgs[0])[:120],
                "recommendation": "תמונות המציגות מלונות, מבצעים, מוצרים או קישורים חייבות לכלול תיאור מפורט ב-alt ולא להישאר ריקות."
            })
            
        if poor_alt_imgs:
            issues.append({
                "type": "poor_alt",
                "severity": "medium",
                "message": f"נמצאו {len(poor_alt_imgs)} תמונות עם מאפיין alt סתמי או סיומת קובץ (למשל 'תמונה', 'לוגו', '1.png')",
                "element": str(poor_alt_imgs[0])[:120],
                "recommendation": "החלף את ה-alt בתיאור בעל משמעות של מה שנראה בתמונה עבור עיוורים ולקויי ראייה."
            })

    # -------------------------------------------------------------
    # 9. ULTRA-STRICT: Event Posters / Flyers / Deals Text Accessibility (WCAG 1.4.5 & ת"י 5568)
    # "אם יש תמונה עם פרטים של אירוע, הפרטים צריכים להיות כתובים גם טקסטואלית"
    # -------------------------------------------------------------
    event_images_without_text = []
    total_event_images = 0
    
    for img in imgs:
        src = img.get("src") or img.get("data-src") or ""
        alt = (img.get("alt") or "").strip()
        fname = src.split("/")[-1].lower() if "/" in src else src.lower()
        
        # Determine if this image represents an event, hotel deal, flyer, poster, or campaign graphic
        is_event_candidate = any(k in fname for k in EVENT_KEYWORDS)
        
        # Also check parent container
        parent_card = img.find_parent(lambda t: t.name in ["div", "article", "li", "section", "figure"] and any(c in str(t.get("class", [])) for c in ["card", "item", "deal", "hotel", "banner", "event", "post", "flyer", "promo"]))
        if parent_card and not is_event_candidate:
            # Check if image has banner/card proportions or attributes
            w = img.get("width")
            if w and str(w).isdigit() and int(w) >= 200:
                is_event_candidate = True
            elif "ratio" in str(img.find_parent().get("class", [])):
                is_event_candidate = True
                
        if is_event_candidate:
            total_event_images += 1
            
            # 1. Does the image have an extensive descriptive alt describing the event details?
            has_detailed_alt = len(alt) >= 25 and not any(alt.lower() == k for k in SUSPICIOUS_ALTS)
            
            # 2. Is there live HTML text in the enclosing card/container describing dates, location, details?
            has_live_text = False
            if parent_card:
                # Text inside the card excluding the img tag
                card_text = parent_card.get_text(separator=" ", strip=True)
                # If card text has substantial information (> 45 chars) with dates/numbers or keywords
                if len(card_text) >= 45:
                    has_live_text = True
                    
            if not has_detailed_alt and not has_live_text:
                event_images_without_text.append({
                    "src": fname,
                    "element": str(img)[:120],
                    "alt": alt
                })

    if total_event_images > 0 and len(event_images_without_text) == 0:
        compliance_checks.append({
            "id": "wcag_images_of_text",
            "name": "הנגשת כרזות, פליירים ומודעות אירועים כטקסט חי",
            "standard": "WCAG 1.4.5 (Images of Text) & ת\"י 5568",
            "status": "passed",
            "details": f"אותרו {total_event_images} כרזות ותמונות אירועים/מבצעים. כל הפרטים מונגשים במלואם כטקסט חי ב-HTML או ב-alt מפורט."
        })
    elif total_event_images > 0:
        compliance_checks.append({
            "id": "wcag_images_of_text",
            "name": "הנגשת כרזות, פליירים ומודעות אירועים כטקסט חי",
            "standard": "WCAG 1.4.5 (Images of Text) & ת\"י 5568",
            "status": "failed",
            "details": f"נמצאו {len(event_images_without_text)} מתוך {total_event_images} כרזות/תמונות של אירועים, כנסים או מבצעים שבהן פרטי האירוע (תאריכים, מיקום, שעות, מחיר) נעולים בתמונה ללא טקסט חי ב-HTML!"
        })
        issues.append({
            "type": "event_image_without_text",
            "severity": "critical",
            "message": f"קריטי לנגישות: {len(event_images_without_text)} כרזות/תמונות אירועים ומבצעים ללא פירוט טקסטואלי מקביל (תאריכים ומידע חיוני נעולים בפיקסלים)",
            "element": event_images_without_text[0]["element"],
            "recommendation": "לפי תקן ת\"י 5568 ו-WCAG 1.4.5 (Images of Text), חובה שכל פרט המופיע בכרזה (שם האירוע, תאריכים, מיקום, שעות, תוכנית ועלויות) יופיע גם כטקסט חי בקוד ה-HTML (למשל בפסקת תיאור מתחת לתמונה) או בתוך alt מפורט במיוחד לקוראי מסך."
        })
    else:
        compliance_checks.append({
            "id": "wcag_images_of_text",
            "name": "הנגשת כרזות, פליירים ומודעות אירועים כטקסט חי",
            "standard": "WCAG 1.4.5 (Images of Text) & ת\"י 5568",
            "status": "passed",
            "details": "לא אותרו כרזות גרפיות או מודעות אירועים מבוססות תמונה הדורשות פירוט טקסטואלי מקביל."
        })

    # -------------------------------------------------------------
    # 10. STRICT: Accessibility Statement (חוק שוויון זכויות לאנשים עם מוגבלות - תקנה 35 & ת"י 5568)
    # -------------------------------------------------------------
    a11y_keywords = ["הצהרת נגישות", "הסדרי נגישות", "הצהרת הנגישות", "רכז נגישות", "נגישות באתר", "accessibility statement"]
    found_real_a11y_link = False
    found_fake_a11y_link = False
    
    for a in soup.find_all("a"):
        txt = a.get_text(separator=" ", strip=True).lower()
        href = (a.get("href") or "").strip()
        title = (a.get("title") or "").lower()
        aria = (a.get("aria-label") or "").lower()
        
        matches_kw = any(k in txt or k in title or k in aria for k in a11y_keywords) or any(k in href.lower() for k in ["accessibility", "a11y", "negishut"])
        if matches_kw:
            if href and href not in ["#", "javascript:void(0)", "javascript:;", ""]:
                found_real_a11y_link = True
                break
            else:
                found_fake_a11y_link = True

    if found_real_a11y_link:
        compliance_checks.append({
            "id": "wcag_a11y_statement",
            "name": "הצהרת נגישות והסדרי נגישות כחוק",
            "standard": "חוק שוויון זכויות לאנשים עם מוגבלות (תקנה 35) & ת\"י 5568",
            "status": "passed",
            "details": "נמצא קישור פעיל ומקושר לדף הצהרת נגישות והסדרי נגישות כנדרש בחוק הישראלי."
        })
    elif found_fake_a11y_link:
        compliance_checks.append({
            "id": "wcag_a11y_statement",
            "name": "הצהרת נגישות והסדרי נגישות כחוק",
            "standard": "חוק שוויון זכויות לאנשים עם מוגבלות (תקנה 35) & ת\"י 5568",
            "status": "failed",
            "details": "נמצא אזכור נגישות אך הקישור מדומה (href='#') ואינו מוביל לדף הצהרת נגישות מפורט כחוק."
        })
        issues.append({
            "type": "fake_a11y_statement_link",
            "severity": "critical",
            "message": "קישור הצהרת נגישות מדומה (href='#') - אינו מוביל לדף הצהרה אמיתי!",
            "element": "<a href='#'>נגישות</a>",
            "recommendation": "לפי תקנה 35, חובה לקשר לדף הצהרת נגישות הכולל פירוט עמידה בתקן ת\"י 5568, פרטי רכז נגישות והסדרי נגישות פיזיים ודיגיטליים."
        })
    else:
        compliance_checks.append({
            "id": "wcag_a11y_statement",
            "name": "הצהרת נגישות והסדרי נגישות כחוק",
            "standard": "חוק שוויון זכויות לאנשים עם מוגבלות (תקנה 35) & ת\"י 5568",
            "status": "failed",
            "details": "לא נמצא קישור להצהרת נגישות או להסדרי נגישות בדף. חובה חוקית בישראל לכל אתר מסחרי או ציבורי!"
        })
        issues.append({
            "type": "missing_a11y_statement",
            "severity": "critical",
            "message": "חסר קישור להצהרת נגישות / הסדרי נגישות באתר (חובה חוקית בישראל - תקנה 35)",
            "element": "<footer>",
            "recommendation": "הוסף בתחתית האתר (Footer) קישור בולט: 'הצהרת נגישות' המוביל לדף ייעודי עם פרטי רכז הנגישות ורמת הנגישות."
        })

    # -------------------------------------------------------------
    # 11. STRICT: Accessible Names for Links & Icons (WCAG 2.4.4 & 4.1.2)
    # -------------------------------------------------------------
    anchors = soup.find_all("a")
    empty_links = []
    vague_anchors = 0
    
    for a in anchors:
        txt = a.get_text(strip=True)
        aria = a.get("aria-label") or a.get("aria-labelledby") or a.get("title")
        child_img = a.find("img")
        img_alt = child_img.get("alt", "").strip() if child_img else ""
        
        # Link must have an accessible name
        if not txt and not aria and not img_alt:
            empty_links.append(a)
            
        # Link text must be meaningful (not vague like "click here")
        txt_lower = txt.lower()
        if txt_lower in VAGUE_LINK_WORDS and not aria:
            vague_anchors += 1

    if len(anchors) > 0 and len(empty_links) == 0:
        compliance_checks.append({
            "id": "wcag_empty_links",
            "name": "שמות ותוויות נגישות לקישורים (Accessible Name)",
            "standard": "WCAG 2.4.4 & 4.1.2 & ת\"י 5568",
            "status": "passed",
            "details": f"כל {len(anchors)} הקישורים בדף כוללים טקסט גלוי, תווית aria-label או תמונת alt המגדירים את היעד."
        })
    elif len(anchors) > 0:
        compliance_checks.append({
            "id": "wcag_empty_links",
            "name": "שמות ותוויות נגישות לקישורים (Accessible Name)",
            "standard": "WCAG 2.4.4 & 4.1.2 & ת\"י 5568",
            "status": "failed",
            "details": f"נמצאו {len(empty_links)} קישורים ללא שם נגיש כלל (למשל קישורי אייקון, רשתות חברתיות או שיתוף ללא aria-label)."
        })
        issues.append({
            "type": "empty_link",
            "severity": "high",
            "message": f"נמצאו {len(empty_links)} קישורים ללא טקסט או תווית נגישה (aria-label)",
            "element": str(empty_links[0])[:120],
            "recommendation": "הוסף מאפיין aria-label='תיאור היעד' לכל קישור אייקון (למשל: 'עקוב אחרינו בפייסבוק', 'שתף בוואטסאפ')."
        })
    else:
        compliance_checks.append({
            "id": "wcag_empty_links",
            "name": "שמות ותוויות נגישות לקישורים (Accessible Name)",
            "standard": "WCAG 2.4.4 & 4.1.2 & ת\"י 5568",
            "status": "passed",
            "details": "לא נמצאו קישורים בדף."
        })

    # -------------------------------------------------------------
    # 12. Link Purpose / Contextual Anchor text (WCAG 2.4.4)
    # -------------------------------------------------------------
    if len(anchors) > 0 and vague_anchors == 0:
        compliance_checks.append({
            "id": "wcag_link_purpose",
            "name": "טקסט קישורים בעל משמעות הקשרית",
            "standard": "WCAG 2.4.4 (Link Purpose) & ת\"י 5568",
            "status": "passed",
            "details": f"כל {len(anchors)} הקישורים בדף כוללים טקסט בעל משמעות (ללא ביטויים עמומים כגון 'לחץ כאן' או 'לפרטים')."
        })
    elif len(anchors) > 0:
        compliance_checks.append({
            "id": "wcag_link_purpose",
            "name": "טקסט קישורים בעל משמעות הקשרית",
            "standard": "WCAG 2.4.4 (Link Purpose) & ת\"י 5568",
            "status": "failed",
            "details": f"נמצאו {vague_anchors} קישורים עם טקסט סתמי כגון 'לחץ כאן' או 'לפרטים' ללא תיאור יעד ברור לקוראי מסך."
        })
        issues.append({
            "type": "vague_anchor_text",
            "severity": "medium",
            "message": f"נמצאו {vague_anchors} קישורים עם טקסט עמום ולא אינפורמטיבי ('לחץ כאן', 'לפרטים נוספים')",
            "element": "<a>לחץ כאן</a>",
            "recommendation": "החלף את הטקסט בתיאור יעד ממשי (למשל: 'להזמנת נופש במלון X', 'לצפייה בפרטי הכנס') או הוסף aria-label מפורט."
        })
    else:
        compliance_checks.append({
            "id": "wcag_link_purpose",
            "name": "טקסט קישורים בעל משמעות הקשרית",
            "standard": "WCAG 2.4.4 (Link Purpose) & ת\"י 5568",
            "status": "passed",
            "details": "לא נמצאו קישורים בדף."
        })

    # -------------------------------------------------------------
    # 13. Skip Link / Bypass Blocks (WCAG 2.4.1 & ת"י 5568)
    # -------------------------------------------------------------
    skip_link_found = False
    for a in anchors[:10]:
        txt = a.get_text(strip=True).lower()
        href = (a.get("href") or "").lower()
        if "דילוג" in txt or "דלג" in txt or "skip" in txt or "#main" in href or "#content" in href:
            skip_link_found = True
            break
            
    if skip_link_found:
        compliance_checks.append({
            "id": "wcag_skip_link",
            "name": "מנגנון דילוג ישיר לתוכן מרכזי (Skip to Content)",
            "standard": "WCAG 2.4.1 (Bypass Blocks) & ת\"י 5568",
            "status": "passed",
            "details": "קיים קישור דילוג בראש הדף המאפשר למשתמשי מקלדת לעקוף את תפריטי הניווט ולעבור ישירות לתוכן."
        })
    else:
        compliance_checks.append({
            "id": "wcag_skip_link",
            "name": "מנגנון דילוג ישיר לתוכן מרכזי (Skip to Content)",
            "standard": "WCAG 2.4.1 (Bypass Blocks) & ת\"י 5568",
            "status": "failed",
            "details": "לא נמצא קישור דילוג ('דלג לתוכן מרכזי') בראש הדף. משתמשי מקלדת נאלצים לעבור את כל התפריטים בכל טעינה."
        })
        issues.append({
            "type": "missing_skip_link",
            "severity": "medium",
            "message": "חסר קישור 'דלג לתוכן מרכזי' (Skip to Content) בראש הדף",
            "element": "<body>",
            "recommendation": "הוסף קישור ראשון בדף: <a href='#main' class='skip-link'>דלג לתוכן מרכזי</a> שיוצג בפוקוס מקלדת."
        })

    # -------------------------------------------------------------
    # 14. Target Blank Warnings (WCAG 3.2.5 & ת"י 5568)
    # -------------------------------------------------------------
    target_blanks = soup.find_all("a", attrs={"target": "_blank"})
    unwarned_blanks = 0
    for a in target_blanks:
        aria = (a.get("aria-label") or "").lower()
        txt = a.get_text(strip=True).lower()
        title = (a.get("title") or "").lower()
        if "חלון חדש" not in aria and "חלון חדש" not in txt and "חלון חדש" not in title and "new tab" not in aria and "new tab" not in txt:
            unwarned_blanks += 1
            
    if len(target_blanks) == 0:
        compliance_checks.append({
            "id": "wcag_target_blank",
            "name": "התרעה על פתיחת כרטיסיות חדשות (target=_blank)",
            "standard": "WCAG 3.2.5 (Change on Request) & ת\"י 5568",
            "status": "passed",
            "details": "אין קישורים הנפתחים בחלון או כרטיסייה חדשה ללא שליטת המשתמש."
        })
    elif unwarned_blanks == 0:
        compliance_checks.append({
            "id": "wcag_target_blank",
            "name": "התרעה על פתיחת כרטיסיות חדשות (target=_blank)",
            "standard": "WCAG 3.2.5 (Change on Request) & ת\"י 5568",
            "status": "passed",
            "details": f"כל {len(target_blanks)} הקישורים הנפתחים בחלון חדש כוללים התרעה מפורשת לקורא מסך."
        })
    else:
        compliance_checks.append({
            "id": "wcag_target_blank",
            "name": "התרעה על פתיחת כרטיסיות חדשות (target=_blank)",
            "standard": "WCAG 3.2.5 (Change on Request) & ת\"י 5568",
            "status": "failed",
            "details": f"נמצאו {unwarned_blanks} קישורים עם target='_blank' ללא התרעה קולית או ויזואלית ('נפתח בחלון חדש')."
        })
        issues.append({
            "type": "target_blank_no_warning",
            "severity": "low",
            "message": f"נמצאו {unwarned_blanks} קישורים הנפתחים בחלון חדש ללא אזהרה לקוראי מסך",
            "element": "<a target='_blank'>",
            "recommendation": "הוסף מאפיין aria-label עם הסיומת '(נפתח בחלון חדש)' או טקסט ייעודי לקוראי מסך (sr-only)."
        })

    # -------------------------------------------------------------
    # 15. Tabindex and Keyboard Navigation Order (WCAG 2.4.3)
    # -------------------------------------------------------------
    positive_tabindexes = []
    for tag in soup.find_all(attrs={"tabindex": True}):
        ti = tag.get("tabindex")
        try:
            if int(ti) > 0:
                positive_tabindexes.append(tag)
        except (ValueError, TypeError):
            pass
            
    if len(positive_tabindexes) == 0:
        compliance_checks.append({
            "id": "wcag_tabindex_focus",
            "name": "סדר ניווט ומיקוד מקלדת תקין (ללא tabindex חיובי)",
            "standard": "WCAG 2.4.3 (Focus Order)",
            "status": "passed",
            "details": "סדר המיקוד הטבעי של המקלדת נשמר כראוי (ללא שימוש ב-tabindex חיובי שמשבש את הסדר)."
        })
    else:
        compliance_checks.append({
            "id": "wcag_tabindex_focus",
            "name": "סדר ניווט ומיקוד מקלדת תקין (ללא tabindex חיובי)",
            "standard": "WCAG 2.4.3 (Focus Order)",
            "status": "failed",
            "details": f"נמצאו {len(positive_tabindexes)} אלמנטים עם tabindex חיובי (>0) המשבשים את הניווט הטבעי במקלדת."
        })
        issues.append({
            "type": "positive_tabindex",
            "severity": "medium",
            "message": f"שימוש ב-tabindex חיובי ({len(positive_tabindexes)} אלמנטים) משבש את סדר הניווט במקלדת",
            "element": str(positive_tabindexes[0])[:120],
            "recommendation": "השתמש רק ב-tabindex='0' (להוספה לרצף) או tabindex='-1' (לפוקוס תוכנתי). הימנע מערכים חיוביים (1, 2, 3...)."
        })

    # -------------------------------------------------------------
    # 16. Multimedia Autoplay without Mute (WCAG 1.4.2)
    # -------------------------------------------------------------
    media_tags = soup.find_all(["video", "audio"])
    noisy_autoplay = 0
    for m in media_tags:
        if m.has_attr("autoplay") and not m.has_attr("muted"):
            noisy_autoplay += 1
            
    if noisy_autoplay == 0:
        compliance_checks.append({
            "id": "wcag_audio_control",
            "name": "בקרת השמעה אוטומטית (Audio/Video)",
            "standard": "WCAG 1.4.2 (Audio Control) & ת\"י 5568",
            "status": "passed",
            "details": "אין רכיבי וידאו או אודיו המנגנים צליל אוטומטית ללא שליטת המשתמש (מניעת הפרעה לקורא מסך)."
        })
    else:
        compliance_checks.append({
            "id": "wcag_audio_control",
            "name": "בקרת השמעה אוטומטית (Audio/Video)",
            "standard": "WCAG 1.4.2 (Audio Control) & ת\"י 5568",
            "status": "failed",
            "details": f"נמצאו {noisy_autoplay} רכיבי מדיה המנגנים צליל אוטומטית. חובה להשתיק (muted) או להסיר autoplay."
        })
        issues.append({
            "type": "audio_control",
            "severity": "critical",
            "message": "רכיב וידאו או אודיו מנגן צליל אוטומטית (autoplay ללא muted)",
            "element": "<video/audio autoplay>",
            "recommendation": "הוסף מאפיין muted או הסר autoplay כדי למנוע הפרעה למשתמשי קוראי מסך."
        })

    passed_checks = [c for c in compliance_checks if c["status"] == "passed"]
    failed_checks = [c for c in compliance_checks if c["status"] == "failed"]

    return {
        "html_lang": lang or "חסר",
        "html_dir": dir_attr or "לא מוגדר",
        "h1_count": h1_count,
        "total_headings": len(headings),
        "heading_tree": heading_tree,
        "landmarks": {
            "has_main": has_main,
            "has_header": has_header,
            "has_footer": has_footer,
            "has_nav": has_nav
        },
        "unlabeled_inputs_count": unlabeled_inputs,
        "unnamed_buttons_count": unnamed_buttons,
        "total_event_images": total_event_images,
        "event_images_without_text_count": len(event_images_without_text),
        "compliance_checks": compliance_checks,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "passed_count": len(passed_checks),
        "failed_count": len(failed_checks),
        "issues": issues
    }
