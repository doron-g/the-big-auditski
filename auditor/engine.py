import asyncio
import time
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import httpx

from .links import audit_links
from .images import audit_images
from .accessibility import audit_accessibility
from .seo_meta import audit_seo_meta
from .security import audit_security_and_hygiene
from .todo_builder import build_todo_list

async def run_full_audit(
    url: str = None, 
    html_content: str = None, 
    check_live_status: bool = True,
    scope_path: str = None,
    exclude_header_footer: bool = False
) -> dict:
    start_time = time.time()
    response_headers = {}
    http_status = 200
    load_time_ms = 0
    content_size_kb = 0
    
    # 1. Fetch HTML if URL provided
    if url:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 ClientLaunchAuditor/1.0"
        }
        
        t0 = time.time()
        try:
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=12.0, verify=False) as client:
                resp = await client.get(url)
                http_status = resp.status_code
                response_headers = {k.lower(): v for k, v in resp.headers.items()}
                html_content = resp.text
                url = str(resp.url) # update to final url after redirects
                load_time_ms = round((time.time() - t0) * 1000)
                content_size_kb = round(len(resp.content) / 1024, 1)
        except Exception as e:
            return {
                "success": False,
                "error": f"לא ניתן לטעון את האתר בכתובת {url}: {str(e)}",
                "target_url": url
            }
            
    if not html_content:
        return {
            "success": False,
            "error": "לא סופק תוכן HTML או כתובת אתר לבדיקה."
        }
        
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Auto-detect subpath if url was provided and scope_path was not set
    if url and not scope_path:
        u_path = urlparse(url).path
        if u_path and u_path.strip("/") != "":
            scope_path = u_path

    # Optionally exclude global parent header & footer
    if exclude_header_footer:
        for tag in soup.find_all(["header", "footer"]):
            tag.decompose()
    
    # 2. Run module audits concurrently where appropriate
    links_res, images_res, seo_res = await asyncio.gather(
        audit_links(soup, url, check_live_status=check_live_status, scope_path=scope_path),
        audit_images(soup, url, check_live_status=check_live_status),
        audit_seo_meta(soup, url, check_live_status=check_live_status)
    )
    
    a11y_res = audit_accessibility(soup)
    security_res = audit_security_and_hygiene(soup, url, response_headers)
    
    raw_results = {
        "links": links_res,
        "images": images_res,
        "a11y": a11y_res,
        "seo": seo_res,
        "security": security_res
    }
    
    # 3. Build TODO list and scoring
    todo_data = build_todo_list(raw_results)
    
    total_duration_sec = round(time.time() - start_time, 2)
    
    return {
        "success": True,
        "target_url": url or "HTML קוד ישיר",
        "domain": urlparse(url).netloc if url else "קוד מקור",
        "scope_path": scope_path,
        "out_of_scope_links_count": links_res.get("out_of_scope_count", 0),
        "scan_time": time.strftime("%d/%m/%Y %H:%M:%S"),
        "scan_duration_sec": total_duration_sec,
        "load_time_ms": load_time_ms,
        "content_size_kb": content_size_kb,
        "http_status": http_status,
        "overall_score": todo_data["overall_score"],
        "a11y_score": todo_data["a11y_score"],
        "tech_score": todo_data["tech_score"],
        "category_scores": todo_data["category_scores"],
        "verdict": todo_data["verdict"],
        "todos": todo_data["todos"],
        "a11y_todos": todo_data["a11y_todos"],
        "tech_todos": todo_data["tech_todos"],
        "a11y_compliance": {
            "passed_checks": a11y_res.get("passed_checks", []),
            "failed_checks": a11y_res.get("failed_checks", []),
            "all_checks": a11y_res.get("compliance_checks", []),
            "passed_count": a11y_res.get("passed_count", 0),
            "failed_count": a11y_res.get("failed_count", 0)
        },
        "seo": raw_results["seo"],
        "raw_results": raw_results
    }
