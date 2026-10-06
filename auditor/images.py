import asyncio
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import httpx

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

async def check_single_image(client: httpx.AsyncClient, url: str) -> dict:
    try:
        response = await client.head(url, follow_redirects=True, timeout=5.0)
        if response.status_code in [405, 403, 400]:
            response = await client.get(url, follow_redirects=True, timeout=5.0)
            
        content_type = response.headers.get("content-type", "")
        content_length = response.headers.get("content-length")
        size_kb = round(int(content_length) / 1024, 1) if content_length and content_length.isdigit() else None
        
        return {
            "status_code": response.status_code,
            "ok": 200 <= response.status_code < 400,
            "content_type": content_type,
            "size_kb": size_kb,
            "error": None
        }
    except Exception as e:
        return {"status_code": 0, "ok": False, "error": str(e), "size_kb": None, "content_type": ""}

async def audit_images(soup: BeautifulSoup, base_url: str, check_live_status: bool = True) -> dict:
    img_tags = soup.find_all("img")
    total_imgs = len(img_tags)
    
    images_data = []
    issues = []
    urls_to_test = {}
    
    # 1. Favicon check
    favicon_link = soup.find("link", rel=lambda r: r and any("icon" in str(x).lower() for x in (r if isinstance(r, list) else [r])))
    has_favicon = favicon_link is not None
    if not has_favicon:
        issues.append({
            "type": "missing_favicon",
            "severity": "high",
            "message": "לא הוגדר Favicon (אייקון אתר בלשונית הדפדפן)",
            "element": "<head>",
            "recommendation": "הוסף תגית Favicon ב-<head>: <link rel='icon' type='image/png' href='/favicon.png'>"
        })
        
    missing_alt_items = []
    empty_alt_content_items = []
    poor_alt_items = []
    event_images_missing_text = []

    # 2. Audit each <img>
    for idx, img in enumerate(img_tags):
        src = img.get("src", "").strip()
        data_src = img.get("data-src", "").strip() # Support lazy-loaded images
        effective_src = src or data_src
        
        alt = img.get("alt")
        role = img.get("role", "")
        aria_hidden = img.get("aria-hidden", "") == "true"
        is_decorative = role in ["presentation", "none"] or aria_hidden
        
        width = img.get("width")
        height = img.get("height")
        loading = img.get("loading")
        
        fname = effective_src.split("/")[-1].lower() if "/" in effective_src else effective_src.lower()
        is_event_candidate = any(k in fname for k in EVENT_KEYWORDS)
        
        # Check parent container for event/deal cards
        parent_card = img.find_parent(lambda t: t.name in ["div", "article", "li", "section", "figure"] and any(c in str(t.get("class", [])) for c in ["card", "item", "deal", "hotel", "banner", "event", "post", "flyer", "promo"]))
        if parent_card and not is_event_candidate:
            if (width and str(width).isdigit() and int(width) >= 200) or "ratio" in str(img.find_parent().get("class", [])):
                is_event_candidate = True
        
        has_valid_alt = False
        if alt is not None:
            if alt.strip() != "":
                has_valid_alt = True
            elif is_decorative:
                has_valid_alt = True
                
        img_info = {
            "index": idx + 1,
            "src": effective_src,
            "alt": alt,
            "has_alt": has_valid_alt,
            "alt_text": alt if alt is not None else "",
            "is_decorative": is_decorative,
            "is_event_flyer": is_event_candidate,
            "has_dimensions": bool(width and height),
            "width": width,
            "height": height,
            "loading": loading,
            "status_code": None,
            "status_ok": None,
            "size_kb": None,
            "issues": []
        }
        
        # Check missing or empty src
        if not effective_src:
            img_info["issues"].append("תגית תמונה ללא מקור (src)")
            issues.append({
                "type": "missing_src",
                "severity": "critical",
                "message": f"תמונה מס' {idx+1} חסרת נתיב מקור (src ריק)",
                "element": str(img)[:120],
                "recommendation": "הגדר נתיב תמונה תקין ב-src או הסר את התגית."
            })
            images_data.append(img_info)
            continue
            
        # Resolved full URL
        resolved_url = urljoin(base_url, effective_src) if base_url else effective_src
        img_info["full_url"] = resolved_url
        
        # Check Alt attribute rigorously
        if alt is None:
            img_info["issues"].append("חסר מאפיין alt (נגישות ו-SEO)")
            missing_alt_items.append(effective_src)
        elif alt.strip() == "":
            if not is_decorative:
                img_info["issues"].append("מאפיין alt ריק בתמונת תוכן (אינה דקורטיבית!)")
                empty_alt_content_items.append(effective_src)
        else:
            alt_clean = alt.strip().lower()
            if alt_clean in SUSPICIOUS_ALTS or alt_clean.endswith(('.jpg', '.png', '.webp', '.jpeg', '.svg', '.gif')):
                img_info["issues"].append(f"מאפיין alt סתמי או סיומת קובץ ('{alt}')")
                poor_alt_items.append(effective_src)
                
        # Check Event/Flyer image text accessibility
        if is_event_candidate:
            has_detailed_alt = alt is not None and len(alt.strip()) >= 25
            has_card_text = False
            if parent_card:
                c_text = parent_card.get_text(separator=" ", strip=True)
                if len(c_text) >= 45:
                    has_card_text = True
                    
            if not has_detailed_alt and not has_card_text:
                img_info["issues"].append("כרזה/אירוע ללא פירוט טקסטואלי מקביל (ת\"י 5568)")
                event_images_missing_text.append(effective_src)
                
        # Dimensions check (CLS)
        if not (width and height):
            style = img.get("style", "")
            has_style_dims = "width" in style and "height" in style
            if not has_style_dims:
                img_info["issues"].append("חסרים ממדים מוגדרים (width ו-height)")
                
        # Heavy format check
        src_lower = effective_src.lower()
        if ".bmp" in src_lower or ".tiff" in src_lower:
            img_info["issues"].append("פורמט תמונה כבד (BMP/TIFF)")
            
        images_data.append(img_info)
        
        # Add to test queue if http(s)
        if resolved_url.startswith(("http://", "https://")):
            if resolved_url not in urls_to_test:
                urls_to_test[resolved_url] = []
            urls_to_test[resolved_url].append(idx)
            
    # Check live HTTP status if requested
    if check_live_status and urls_to_test and base_url:
        distinct_urls = list(urls_to_test.keys())[:30] # Fast cap
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ClientLaunchAuditor/1.0"}
        
        async with httpx.AsyncClient(headers=headers, verify=False, timeout=6.0) as client:
            tasks = [check_single_image(client, u) for u in distinct_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for u, res in zip(distinct_urls, results):
                if isinstance(res, Exception):
                    info = {"status_code": 0, "ok": False, "error": str(res), "size_kb": None}
                else:
                    info = res
                    
                for i_idx in urls_to_test[u]:
                    images_data[i_idx]["status_code"] = info.get("status_code")
                    images_data[i_idx]["status_ok"] = info.get("ok")
                    images_data[i_idx]["size_kb"] = info.get("size_kb")
                    
                    if not info.get("ok"):
                        status_code = info.get("status_code")
                        images_data[i_idx]["issues"].append(f"תמונה שבורה (קוד {status_code or 'שגיאת רשת'})")
                        issues.append({
                            "type": "broken_image",
                            "severity": "critical",
                            "message": f"תמונה שבורה לא נטענת: {u} (קוד {status_code or 'אין מענה'})",
                            "element": f"<img src='{u}' />",
                            "recommendation": "וודא שהקובץ קיים בשרת בנתיב המבוקש והעלה את התמונה מחדש."
                        })
                    elif info.get("size_kb") and info["size_kb"] > 1000:
                        images_data[i_idx]["issues"].append(f"תמונה כבדה במיוחד ({info['size_kb']} KB)")
                        issues.append({
                            "type": "oversized_image",
                            "severity": "medium",
                            "message": f"תמונה כבדה מאוד ({info['size_kb']} KB): {u}",
                            "element": f"<img src='{u}' />",
                            "recommendation": "דחוס את התמונה בעזרת כלי כיווץ (TinyPNG/Squoosh) או המר ל-WebP להאצת הדף."
                        })
                        
    # Aggregated issue cards for the images module
    if missing_alt_items:
        issues.append({
            "type": "missing_alt",
            "severity": "high",
            "message": f"נמצאו {len(missing_alt_items)} תמונות ללא תגית alt כלל",
            "element": f"<img src='{missing_alt_items[0]}' />",
            "recommendation": "הוסף מאפיין alt='...' המתאר את תוכן התמונה עבור קוראי מסך ומנועי חיפוש."
        })
        
    if empty_alt_content_items:
        issues.append({
            "type": "empty_alt_content_image",
            "severity": "high",
            "message": f"נמצאו {len(empty_alt_content_items)} תמונות תוכן/כרטיסים עם מאפיין alt ריק (אינן דקורטיביות)",
            "element": f"<img src='{empty_alt_content_items[0]}' alt='' />",
            "recommendation": "תמונות המציגות תוכן (מבצעים, חדרים, אירועים) חייבות לכלול תיאור ב-alt. השאר alt ריק רק לרכיבי גרפיקה קישוטיים (עם role='presentation')."
        })
        
    if poor_alt_items:
        issues.append({
            "type": "poor_alt",
            "severity": "medium",
            "message": f"נמצאו {len(poor_alt_items)} תמונות עם מאפיין alt סתמי או סיומת קובץ (למשל 'image', '1.png', 'לוגו')",
            "element": f"<img src='{poor_alt_items[0]}' />",
            "recommendation": "החלף את ה-alt בתיאור אמיתי של התוכן, לא 'image' או שם הקובץ."
        })
        
    if event_images_missing_text:
        issues.append({
            "type": "event_image_without_text",
            "severity": "critical",
            "message": f"נמצאו {len(event_images_missing_text)} כרזות ותמונות אירועים/מבצעים שבהן כל המידע נעול בגרפיקה ללא טקסט חי ב-HTML!",
            "element": f"<img src='{event_images_missing_text[0]}' />",
            "recommendation": "לפי ת\"י 5568 ו-WCAG 1.4.5, חובה להנגיש את פרטי האירוע (תאריכים, מיקום, תוכנית ומחיר) כטקסט חי ב-HTML או ב-alt מפורט."
        })
        
    missing_alt_count = len(missing_alt_items) + len(empty_alt_content_items)
    broken_img_count = sum(1 for img in images_data if img.get("status_ok") is False)
    
    return {
        "total_images": total_imgs,
        "has_favicon": has_favicon,
        "missing_alt_count": missing_alt_count,
        "poor_alt_count": len(poor_alt_items),
        "event_images_missing_text_count": len(event_images_missing_text),
        "broken_images_count": broken_img_count,
        "images": images_data,
        "issues": issues
    }
