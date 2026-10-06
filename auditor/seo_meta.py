import asyncio
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import httpx

GENERIC_TITLES = {"home", "דף הבית", "untitled", "document", "new tab", "index", "website", "ברוכים הבאים"}

async def check_file_exists(client: httpx.AsyncClient, url: str) -> bool:
    try:
        res = await client.head(url, follow_redirects=True, timeout=4.0)
        if res.status_code in [405, 403]:
            res = await client.get(url, follow_redirects=True, timeout=4.0)
        return res.status_code == 200
    except:
        return False

async def audit_seo_meta(soup: BeautifulSoup, base_url: str, check_live_status: bool = True) -> dict:
    issues = []
    
    # 1. Charset
    charset_meta = soup.find("meta", charset=True) or soup.find("meta", attrs={"http-equiv": lambda h: h and h.lower() == "content-type"})
    has_charset = charset_meta is not None
    if not has_charset:
        issues.append({
            "type": "missing_charset",
            "severity": "high",
            "message": "חסרה הגדרת קידוד תווים (charset) ב-<head>",
            "element": "<head>",
            "recommendation": "הוסף בתחילת ה-<head>: <meta charset='utf-8'>"
        })
        
    # 2. Viewport
    viewport_meta = soup.find("meta", attrs={"name": lambda n: n and n.lower() == "viewport"})
    has_viewport = viewport_meta is not None
    viewport_content = viewport_meta.get("content", "") if viewport_meta else ""
    if not has_viewport:
        issues.append({
            "type": "missing_viewport",
            "severity": "critical",
            "message": "חסרה תגית viewport למובייל. האתר לא יוצג כראוי בטלפונים חכמים!",
            "element": "<head>",
            "recommendation": "הוסף ב-<head>: <meta name='viewport' content='width=device-width, initial-scale=1.0'>"
        })
        
    # 3. Title tag
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    title_len = len(title_text)
    
    if not title_tag or not title_text:
        issues.append({
            "type": "missing_title",
            "severity": "critical",
            "message": "תגית <title> חסרה או ריקה לחלוטין",
            "element": "<head>",
            "recommendation": "הוסף כותרת דף ברורה בתגית <title> (באורך 30-60 תווים) הכוללת את שם העסק ומילת מפתח עיקרית."
        })
    else:
        if title_text.lower() in GENERIC_TITLES:
            issues.append({
                "type": "generic_title",
                "severity": "high",
                "message": f"כותרת הדף כללית מדי ולא מקצועית: '{title_text}'",
                "element": f"<title>{title_text}</title>",
                "recommendation": "שנה את הכותרת לכותרת עסקית ממותגת (למשל: 'עו\"ד כהן - משרד עורכי דין בתל אביב | דף הבית')."
            })
        elif title_len < 20:
            issues.append({
                "type": "short_title",
                "severity": "medium",
                "message": f"כותרת הדף קצרה מדי ({title_len} תווים). מומלץ 30-60 תווים למיקסום SEO",
                "element": f"<title>{title_text}</title>",
                "recommendation": "הרחב את כותרת הדף כדי לנצל את שטח התוצאה בגוגל."
            })
        elif title_len > 65:
            issues.append({
                "type": "long_title",
                "severity": "low",
                "message": f"כותרת הדף ארוכה מדי ({title_len} תווים) ועלולה להיחתך בתוצאות החיפוש של גוגל",
                "element": f"<title>{title_text}</title>",
                "recommendation": "קצר את הכותרת מתחת ל-60 תווים כדי שתוצג במלואה."
            })
            
    # 4. Meta Description
    desc_meta = soup.find("meta", attrs={"name": lambda n: n and n.lower() == "description"})
    desc_text = desc_meta.get("content", "").strip() if desc_meta else ""
    desc_len = len(desc_text)
    
    if not desc_meta or not desc_text:
        issues.append({
            "type": "missing_description",
            "severity": "high",
            "message": "חסר תיאור דף (Meta Description)",
            "element": "<head>",
            "recommendation": "הוסף <meta name='description' content='...'> באורך 120-160 תווים לשיפור אחוז ההקלקות בתוצאות החיפוש."
        })
    else:
        if desc_len < 50:
            issues.append({
                "type": "short_description",
                "severity": "medium",
                "message": f"תיאור הדף קצר מדי ({desc_len} תווים). מומלץ 120-160 תווים",
                "element": f"<meta name='description' content='{desc_text[:30]}...'>",
                "recommendation": "הרחב את תיאור הדף עם משפט שיווקי מושך וקריאה לפעולה."
            })
        elif desc_len > 165:
            issues.append({
                "type": "long_description",
                "severity": "low",
                "message": f"תיאור הדף ארוך מדי ({desc_len} תווים) וייחתך בגוגל",
                "element": f"<meta name='description' content='{desc_text[:30]}...'>",
                "recommendation": "קצר את התיאור לטווח של עד 160 תווים."
            })
            
    # 5. Canonical URL
    canonical_tag = soup.find("link", rel=lambda r: r and "canonical" in (r if isinstance(r, list) else [r]))
    canonical_href = canonical_tag.get("href", "").strip() if canonical_tag else ""
    if not canonical_tag:
        issues.append({
            "type": "missing_canonical",
            "severity": "medium",
            "message": "חסר קישור קנוני (<link rel='canonical'>)",
            "element": "<head>",
            "recommendation": "הוסף תגית קנונית ב-<head> למניעת בעיות תוכן כפול בקידומי SEO."
        })
        
    # 6. Robots Meta Tag (CRITICAL CHECK: noindex leak!)
    robots_meta = soup.find("meta", attrs={"name": lambda n: n and n.lower() == "robots"})
    robots_content = robots_meta.get("content", "").lower() if robots_meta else ""
    if "noindex" in robots_content:
        issues.append({
            "type": "noindex_detected",
            "severity": "critical",
            "message": "🚨 אזהרה קריטית: תגית robots מכילה 'noindex'! האתר לא יופיע בגוגל!",
            "element": str(robots_meta)[:120],
            "recommendation": "הסר מיד את 'noindex' לפני מסירה ללקוח! תגית זו חוסמת את האתר ממנועי חיפוש (נשארת לרוב מסביבת פיתוח)."
        })
    if "nofollow" in robots_content:
        issues.append({
            "type": "nofollow_detected",
            "severity": "high",
            "message": "תגית robots מכילה 'nofollow' החוסמת מעקב קישורים",
            "element": str(robots_meta)[:120],
            "recommendation": "וודא אם נדרש באמת nofollow לכלל הדף, בדרך כלל בפרודקשן יש להסירו."
        })
        
    # 7. Open Graph (Social Sharing)
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    og_img = soup.find("meta", property="og:image")
    og_url = soup.find("meta", property="og:url")
    
    og_data = {
        "title": og_title.get("content", "") if og_title else "",
        "description": og_desc.get("content", "") if og_desc else "",
        "image": og_img.get("content", "") if og_img else "",
        "url": og_url.get("content", "") if og_url else ""
    }
    
    missing_og = []
    if not og_data["title"]: missing_og.append("og:title")
    if not og_data["description"]: missing_og.append("og:description")
    if not og_data["image"]: missing_og.append("og:image")
    
    if missing_og:
        issues.append({
            "type": "missing_open_graph",
            "severity": "medium",
            "message": f"חסרות תגיות Open Graph לשיתוף ברשתות ובוואטסאפ: {', '.join(missing_og)}",
            "element": "<head>",
            "recommendation": "הוסף תגיות og:title, og:description, og:image כדי ששיתוף קישור בוואטסאפ או פייסבוק ייראה מרשים ומקצועי עם תמונה וכותרת."
        })
        
    # 8. Check robots.txt and sitemap.xml if live URL
    has_robots_txt = None
    has_sitemap_xml = None
    if check_live_status and base_url and base_url.startswith(("http://", "https://")):
        robots_url = urljoin(base_url, "/robots.txt")
        sitemap_url = urljoin(base_url, "/sitemap.xml")
        
        async with httpx.AsyncClient(verify=False, timeout=5.0) as client:
            res_robots, res_sitemap = await asyncio.gather(
                check_file_exists(client, robots_url),
                check_file_exists(client, sitemap_url),
                return_exceptions=True
            )
            has_robots_txt = res_robots if isinstance(res_robots, bool) else False
            has_sitemap_xml = res_sitemap if isinstance(res_sitemap, bool) else False
            
        if not has_robots_txt:
            issues.append({
                "type": "missing_robots_txt",
                "severity": "medium",
                "message": "קובץ robots.txt לא נמצא בנתיב /robots.txt",
                "element": "/robots.txt",
                "recommendation": "צור קובץ robots.txt המגדיר הרשאות סריקה ומפנה לקובץ ה-sitemap של האתר."
            })
            
        if not has_sitemap_xml:
            issues.append({
                "type": "missing_sitemap_xml",
                "severity": "medium",
                "message": "מפת אתר sitemap.xml לא נמצאה בנתיב /sitemap.xml",
                "element": "/sitemap.xml",
                "recommendation": "צור והעלה מפת אתר XML וחבר אותה ל-Google Search Console."
            })

    return {
        "title": title_text,
        "title_length": title_len,
        "description": desc_text,
        "description_length": desc_len,
        "canonical": canonical_href,
        "viewport": viewport_content,
        "robots_meta": robots_content or "אינדוקס רגיל (ברירת מחדל)",
        "open_graph": og_data,
        "has_robots_txt": has_robots_txt,
        "has_sitemap_xml": has_sitemap_xml,
        "issues": issues
    }
