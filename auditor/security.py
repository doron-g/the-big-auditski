import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

LOREM_PATTERNS = [
    r"lorem\s+ipsum",
    r"dolor\s+sit\s+amet",
    r"consectetur\s+adipiscing",
    r"לורם\s+איפסום"
]

DUMMY_EMAILS = [
    "test@test.com", "admin@admin.com", "info@example.com", "user@example.com",
    "john@doe.com", "email@example.com", "name@domain.com", "demo@demo.com"
]

DUMMY_PHONES = [
    "123456789", "0123456789", "050-0000000", "0500000000", "555-555-5555", "123-456-7890"
]

CODE_LEAKS = ["TODO:", "FIXME:", "XXX:", "TEMP_KEY", "CHANGEME", "INSERT_KEY_HERE"]

def audit_security_and_hygiene(soup: BeautifulSoup, base_url: str, response_headers: dict = None) -> dict:
    issues = []
    response_headers = response_headers or {}
    
    # 1. HTTPS Check
    is_https = False
    if base_url:
        is_https = base_url.lower().startswith("https://")
        if not is_https and base_url.lower().startswith("http://"):
            issues.append({
                "type": "insecure_http",
                "severity": "critical",
                "message": "האתר מוגש בפרוטוקול לא מאובטח (HTTP במקום HTTPS)",
                "element": base_url,
                "recommendation": "התקן תעודת SSL/TLS (כמו Let's Encrypt) והגדר הפניה אוטומטית מ-HTTP ל-HTTPS (301 Redirect)."
            })
            
    # 2. Mixed content check (if https, any http src?)
    if is_https:
        for tag in soup.find_all(["script", "link", "img", "iframe"]):
            src = tag.get("src") or tag.get("href") or ""
            if src.lower().startswith("http://"):
                issues.append({
                    "type": "mixed_content",
                    "severity": "high",
                    "message": f"נמצא משאב ב-HTTP בלתי מוצפן בדף מאובטח (Mixed Content): {src[:60]}",
                    "element": str(tag)[:120],
                    "recommendation": "שנה את הקישור למשאב ל-HTTPS או לנתיב יחסי (relative protocol //)."
                })
                
    # 3. Security headers audit
    hsts = "strict-transport-security" in response_headers
    x_content_type = "x-content-type-options" in response_headers
    x_frame = "x-frame-options" in response_headers
    csp = "content-security-policy" in response_headers
    
    sec_headers_status = {
        "HSTS": hsts,
        "X-Content-Type-Options": x_content_type,
        "X-Frame-Options": x_frame,
        "Content-Security-Policy": csp
    }
    
    if not hsts and is_https:
        issues.append({
            "type": "missing_hsts",
            "severity": "medium",
            "message": "חסרה כותרת Strict-Transport-Security (HSTS)",
            "element": "HTTP Headers",
            "recommendation": "הגדר כותרת HSTS בשרת כדי לאכוף גלישה ב-HTTPS בלבד."
        })
        
    if not x_frame:
        issues.append({
            "type": "missing_x_frame_options",
            "severity": "medium",
            "message": "חסרה כותרת X-Frame-Options (הגנה מפני Clickjacking)",
            "element": "HTTP Headers",
            "recommendation": "הגדר כותרת X-Frame-Options: SAMEORIGIN או DENY כדי למנוע הטמעת האתר ב-iFrame זר."
        })
        
    if not x_content_type:
        issues.append({
            "type": "missing_x_content_type_options",
            "severity": "low",
            "message": "חסרה כותרת X-Content-Type-Options: nosniff",
            "element": "HTTP Headers",
            "recommendation": "הגדר X-Content-Type-Options: nosniff למניעת ניחוש MIME types על ידי הדפדפן."
        })
        
    # 4. Developer / Staging Placeholders
    page_text = soup.get_text()
    
    # Check Lorem Ipsum
    found_lorem = False
    for pat in LOREM_PATTERNS:
        if re.search(pat, page_text, re.IGNORECASE):
            found_lorem = True
            break
    if found_lorem:
        issues.append({
            "type": "lorem_ipsum_detected",
            "severity": "critical",
            "message": "זוהה טקסט דמה 'לורם איפסום' (Lorem Ipsum) שטרם הוחלף בתוכן אמיתי!",
            "element": "Body Text",
            "recommendation": "החלף את כל טקסט הדמה בתוכן השיווקי הסופי של הלקוח."
        })
        
    # Check Dummy Emails
    for dummy_mail in DUMMY_EMAILS:
        if dummy_mail.lower() in page_text.lower():
            issues.append({
                "type": "dummy_email_detected",
                "severity": "critical",
                "message": f"נמצאה כתובת אימייל לדוגמה: '{dummy_mail}'",
                "element": dummy_mail,
                "recommendation": "החלף את כתובת האימייל בכתובת האמיתית של בית העסק."
            })
            break
            
    # Check Dummy Phones
    for dummy_phone in DUMMY_PHONES:
        if dummy_phone in page_text:
            issues.append({
                "type": "dummy_phone_detected",
                "severity": "high",
                "message": f"נמצא מספר טלפון לדוגמה: '{dummy_phone}'",
                "element": dummy_phone,
                "recommendation": "החלף למספר הטלפון הנכון של הלקוח."
            })
            break
            
    # Check Code TODOs or Debug markers in text
    for marker in CODE_LEAKS:
        if marker in page_text:
            issues.append({
                "type": "code_todo_detected",
                "severity": "high",
                "message": f"נמצאה הערת פיתוח גלויה בדף: '{marker}'",
                "element": marker,
                "recommendation": "מחק הערות פיתוח ומשימות שנשארו בטעות בתוכן."
            })
            break
            
    # 5. Inline script console.log or debugger left behind
    scripts = soup.find_all("script")
    console_log_count = 0
    has_debugger = False
    for scr in scripts:
        scr_content = scr.string or ""
        if "console.log(" in scr_content:
            console_log_count += 1
        if "debugger;" in scr_content:
            has_debugger = True
            
    if has_debugger:
        issues.append({
            "type": "debugger_statement",
            "severity": "critical",
            "message": "נמצאה פקודת 'debugger;' בקוד הסקריפט!",
            "element": "<script>",
            "recommendation": "מחק מיד פקודות debugger; לפני מסירה ללקוח."
        })
    elif console_log_count > 3:
        issues.append({
            "type": "console_logs_in_script",
            "severity": "low",
            "message": f"נמצאו {console_log_count} פקודות console.log() בסקריפטים מוטמעים",
            "element": "<script>",
            "recommendation": "נקה קריאות דיבאג ל-console.log כדי לשמור על קונסולה נקייה בפרודקשן."
        })

    return {
        "is_https": is_https,
        "security_headers": sec_headers_status,
        "found_lorem": found_lorem,
        "issues": issues
    }
