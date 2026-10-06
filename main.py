import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from auditor.engine import run_full_audit

app = FastAPI(
    title="Client Launch Ready - Website Auditor",
    description="מערכת בדיקת מוכנות אתר למסירה ללקוח ודוח משימות לתיקון (TODO)",
    version="1.0.0"
)

# Mount static folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class AuditRequest(BaseModel):
    url: Optional[str] = None
    html: Optional[str] = None
    check_live: bool = True
    scope_path: Optional[str] = None
    exclude_header_footer: bool = False

SAMPLE_DIRTY_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>דף הבית</title>
    <!-- חסר viewport למובייל -->
    <meta name="robots" content="noindex, follow">
    <meta name="description" content="קצר">
</head>
<body>
    <header>
        <nav>
            <a href="/">ראשי</a>
            <a href="/about">אודות</a>
            <a href="https://example-broken-page-xyz123.com/broken">קישור שבור</a>
            <a href="#">לחץ כאן</a>
            <a href="http://staging.clientdomain.local/internal">דומיין פיתוח שנשכח</a>
        </nav>
    </header>

    <div>
        <!-- דילוג כותרות: אין h1, מתחיל מ-h2 ואז h4 -->
        <h2>ברוכים הבאים לאתר העסק החדש</h2>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
        
        <h4>מידע נוסף</h4>
        <p>לפניות במייל: test@test.com או בטלפון: 123456789</p>

        <!-- תמונות ללא alt וללא ממדים -->
        <img src="https://picsum.photos/400/300">
        <img src="https://example.com/non-existing-broken-image.jpg" alt="תמונה">
        <img src="logo.png" alt="logo.png">

        <form action="/contact" method="post">
            <!-- שדה ללא label -->
            <input type="text" placeholder="הכנס את שמך">
            <input type="email" placeholder="אימייל">
            <button></button>
        </form>
    </div>
    
    <script>
        console.log("Debug mode on");
        // debugger;
    </script>
</body>
</html>
"""

@app.get("/")
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Auditor API is running. UI not found."}

@app.post("/api/audit")
async def audit_endpoint(req: AuditRequest):
    if not req.url and not req.html:
        raise HTTPException(status_code=400, detail="נא להזין כתובת אתר או להדביק קוד HTML לבדיקה.")
        
    try:
        results = await run_full_audit(
            url=req.url,
            html_content=req.html,
            check_live_status=req.check_live,
            scope_path=req.scope_path,
            exclude_header_footer=req.exclude_header_footer
        )
        return results
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/api/sample-html")
async def get_sample():
    return {"html": SAMPLE_DIRTY_HTML}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
