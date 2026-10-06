import asyncio
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import httpx

VAGUE_ANCHOR_TEXTS = {
    "לחץ כאן", "כאן", "עוד", "קרא עוד", "לפרטים", "פרטים נוספים", "למידע נוסף", "המשך",
    "click here", "here", "read more", "more", "learn more", "link", "details", "continue"
}

DEV_DOMAIN_PATTERNS = ["localhost", "127.0.0.1", "staging.", "dev.", "test.", "temp.", "wp-staging"]

async def check_single_url(client: httpx.AsyncClient, url: str) -> dict:
    try:
        # Use HEAD first for speed
        response = await client.head(url, follow_redirects=True, timeout=5.0)
        # Some servers block HEAD or return 405 Method Not Allowed, fallback to GET with stream
        if response.status_code in [405, 403, 400]:
            response = await client.get(url, follow_redirects=True, timeout=5.0)
        
        return {
            "status_code": response.status_code,
            "final_url": str(response.url),
            "ok": 200 <= response.status_code < 400,
            "error": None
        }
    except httpx.TimeoutException:
        return {"status_code": 0, "final_url": url, "ok": False, "error": "פסק זמן (Timeout) - השרת לא הגיב"}
    except httpx.ConnectError:
        return {"status_code": 0, "final_url": url, "ok": False, "error": "שגיאת חיבור (DNS / Connection Refused)"}
    except Exception as e:
        return {"status_code": 0, "final_url": url, "ok": False, "error": str(e)}

async def audit_links(
    soup: BeautifulSoup, 
    base_url: str, 
    check_live_status: bool = True,
    scope_path: str = None,
    include_external: bool = True
) -> dict:
    parsed_base = urlparse(base_url) if base_url else None
    base_domain = parsed_base.netloc.lower() if parsed_base else ""
    
    # Normalize scope path if provided, e.g. "/hotels"
    scope_clean = None
    if scope_path and scope_path.strip() and scope_path.strip() != "/":
        scope_clean = "/" + scope_path.strip().strip("/").lower()
    
    a_tags = soup.find_all("a")
    total_found = len(a_tags)
    
    links_data = []
    issues = []
    out_of_scope_count = 0
    urls_to_test = {}  # normalized_url -> list of link indices
    
    for idx, a in enumerate(a_tags):
        raw_href = a.get("href")
        text = a.get_text(strip=True)
        target = a.get("target", "")
        rel = a.get("rel", [])
        if isinstance(rel, list):
            rel_str = " ".join(rel)
        else:
            rel_str = str(rel)
            
        link_info = {
            "index": idx + 1,
            "raw_href": raw_href,
            "text": text,
            "target": target,
            "rel": rel_str,
            "type": "unknown",
            "url": None,
            "status_code": None,
            "status_ok": None,
            "is_in_scope": True,
            "scope_note": "",
            "error": None,
            "issues": []
        }
        
        # Check empty or javascript href
        if not raw_href or raw_href.strip() == "":
            link_info["type"] = "empty"
            link_info["issues"].append("קישור ריק (ללא href)")
            issues.append({
                "type": "empty_href",
                "severity": "critical",
                "message": f"נמצא קישור ריק ללא יעד (טקסט: '{text or 'ללא טקסט'}')",
                "element": str(a)[:120],
                "recommendation": "הוסף כתובת URL תקינה או הסר את תגית ה-<a> אם מדובר בכפתור JavaScript."
            })
            links_data.append(link_info)
            continue
            
        raw_href_clean = raw_href.strip()
        
        if raw_href_clean in ["#", "javascript:void(0)", "javascript:;", "javascript:void(0);"]:
            link_info["type"] = "placeholder"
            link_info["issues"].append("קישור פלייסהולדר (# או javascript:void)")
            issues.append({
                "type": "placeholder_href",
                "severity": "warning",
                "message": f"נמצא קישור פלייסהולדר '{raw_href_clean}' (טקסט: '{text or 'ללא טקסט'}')",
                "element": str(a)[:120],
                "recommendation": "אם זה כפתור שמפעיל פעולת JS, השתמש בתגית <button> במקום <a>, או הזן את כתובת היעד האמיתית."
            })
            links_data.append(link_info)
            continue
            
        if raw_href_clean.startswith("mailto:"):
            link_info["type"] = "mailto"
            email = raw_href_clean[7:].split("?")[0].strip()
            if not email or "@" not in email:
                link_info["issues"].append("כתובת אימייל לא תקינה")
                issues.append({
                    "type": "invalid_mailto",
                    "severity": "warning",
                    "message": f"קישור אימייל לא תקין: '{raw_href_clean}'",
                    "element": str(a)[:120],
                    "recommendation": "וודא שכתובת המייל ב-mailto תקינה ומכילה שפיץ ודומיין אמיתי."
                })
            links_data.append(link_info)
            continue
            
        if raw_href_clean.startswith("tel:"):
            link_info["type"] = "tel"
            phone = raw_href_clean[4:].strip()
            if len(phone) < 6 or "12345" in phone or "00000" in phone:
                link_info["issues"].append("מספר טלפון חשוד כדמה/לא תקין")
                issues.append({
                    "type": "suspicious_tel",
                    "severity": "warning",
                    "message": f"מספר טלפון בקישור נראה כמספר דמה: '{phone}'",
                    "element": str(a)[:120],
                    "recommendation": "עדכן את מספר הטלפון למספר העסק האמיתי של הלקוח."
                })
            links_data.append(link_info)
            continue
            
        if raw_href_clean.startswith("#"):
            link_info["type"] = "anchor"
            # Anchor inside page
            target_id = raw_href_clean[1:]
            if target_id and not soup.find(id=target_id) and not soup.find(attrs={"name": target_id}):
                link_info["issues"].append(f"עוגן פנימי לא קיים: #{target_id}")
                issues.append({
                    "type": "broken_internal_anchor",
                    "severity": "high",
                    "message": f"הקישור מפנה לעוגן #{target_id} שלא קיים בדף",
                    "element": str(a)[:120],
                    "recommendation": f"וודא שקיים אלמנט בדף עם id='{target_id}' או תקן את הקישור."
                })
            links_data.append(link_info)
            continue
            
        # Resolved full URL
        resolved_url = urljoin(base_url, raw_href_clean) if base_url else raw_href_clean
        link_info["url"] = resolved_url
        
        parsed_target = urlparse(resolved_url)
        target_domain = parsed_target.netloc.lower()
        is_internal = bool(base_domain and (target_domain == base_domain or target_domain == ""))
        
        # Scope Filter: Check if link is outside requested subpath
        if scope_clean and is_internal:
            target_path = parsed_target.path.lower().rstrip('/')
            # Link is in scope only if it equals the scope path or is a subpath of it
            is_scoped = target_path == scope_clean or target_path.startswith(scope_clean + "/")
            if not is_scoped:
                link_info["type"] = "parent_scope"
                link_info["is_in_scope"] = False
                link_info["scope_note"] = f"הוחרג: קישור לאתר האב מחוץ ל-{scope_clean}"
                out_of_scope_count += 1
                links_data.append(link_info)
                # Skip checking issues and skip live pinging for parent scope links
                continue
            else:
                link_info["type"] = "internal_scoped"
        elif is_internal:
            link_info["type"] = "internal"
        else:
            link_info["type"] = "external"
            if not include_external:
                link_info["is_in_scope"] = False
                link_info["scope_note"] = "הוחרג: קישור חיצוני"
                out_of_scope_count += 1
                links_data.append(link_info)
                continue
            
        # Target _blank security check
        if target == "_blank":
            if "noopener" not in rel_str and "noreferrer" not in rel_str:
                link_info["issues"].append("target='_blank' ללא rel='noopener'")
                issues.append({
                    "type": "target_blank_security",
                    "severity": "medium",
                    "message": f"קישור חיצוני נפתח בחלון חדש ללא rel='noopener noreferrer': {resolved_url}",
                    "element": str(a)[:120],
                    "recommendation": "הוסף rel='noopener noreferrer' לקישורים עם target='_blank' למניעת פרצת אבטחה (Reverse Tabnabbing)."
                })
                
        # Staging / dev domain check
        for pattern in DEV_DOMAIN_PATTERNS:
            if pattern in resolved_url.lower():
                link_info["issues"].append(f"קישור מכיל דומיין פיתוח/Staging ({pattern})")
                issues.append({
                    "type": "staging_domain_leak",
                    "severity": "critical",
                    "message": f"קישור מכיל כתובת פיתוח שנשכחה: '{resolved_url}'",
                    "element": str(a)[:120],
                    "recommendation": "החלף את הקישור לכתובת הפרודקשן של הלקוח."
                })
                break
                
        # Vague anchor text
        if text.lower() in VAGUE_ANCHOR_TEXTS:
            link_info["issues"].append("טקסט קישור כללי/מעורפל")
            issues.append({
                "type": "vague_anchor_text",
                "severity": "low",
                "message": f"טקסט קישור מעורפל ('{text}'). פוגע בנגישות וב-SEO",
                "element": str(a)[:120],
                "recommendation": "שנה את טקסט הקישור למשמעותי ומדויק יותר, למשל 'קרא עוד על השירותים שלנו' במקום 'קרא עוד'."
            })
            
        links_data.append(link_info)
        
        # Add to check queue if valid http(s)
        if resolved_url.startswith(("http://", "https://")):
            if resolved_url not in urls_to_test:
                urls_to_test[resolved_url] = []
            urls_to_test[resolved_url].append(idx)
            
    # Check live HTTP status if requested and base_url is provided
    if check_live_status and urls_to_test and base_url:
        # Limit to max 40 distinct links to keep scan blazing fast
        distinct_urls = list(urls_to_test.keys())[:40]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ClientLaunchAuditor/1.0"
        }
        
        async with httpx.AsyncClient(headers=headers, verify=False, timeout=6.0) as client:
            tasks = [check_single_url(client, u) for u in distinct_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for u, res in zip(distinct_urls, results):
                if isinstance(res, Exception):
                    status_info = {"status_code": 0, "ok": False, "error": str(res)}
                else:
                    status_info = res
                    
                for l_idx in urls_to_test[u]:
                    links_data[l_idx]["status_code"] = status_info.get("status_code")
                    links_data[l_idx]["status_ok"] = status_info.get("ok")
                    links_data[l_idx]["error"] = status_info.get("error")
                    
                    if not status_info.get("ok"):
                        status_code = status_info.get("status_code")
                        err_text = status_info.get("error") or f"סטטוס שגיאה {status_code}"
                        severity = "critical" if status_code == 404 or status_code == 0 else "high"
                        
                        links_data[l_idx]["issues"].append(f"קישור שבור: {err_text}")
                        issues.append({
                            "type": "broken_link",
                            "severity": severity,
                            "message": f"קישור שבור {u} (קוד {status_code or 'אין מענה'})",
                            "element": f"<a href='{u}'>{links_data[l_idx]['text']}</a>",
                            "recommendation": "תקן את הכתובת לכתובת פעילה או הסר את הקישור אם הדף כבר לא קיים."
                        })
                        
    broken_count = sum(1 for l in links_data if l.get("status_ok") is False or "קישור ריק" in str(l.get("issues")))
    
    return {
        "total_links": total_found,
        "checked_urls_count": len(urls_to_test),
        "broken_links_count": broken_count,
        "out_of_scope_count": out_of_scope_count,
        "scope_path": scope_clean,
        "links": links_data,
        "issues": issues
    }
