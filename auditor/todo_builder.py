WCAG_MAP = {
    "missing_html_lang": "WCAG 3.1.1 (Language of Page) & ת\"י 5568",
    "missing_h1": "WCAG 1.3.1 & 2.4.6 (Headings & Hierarchy) & ת\"י 5568",
    "multiple_h1": "WCAG 1.3.1 (Heading Structure)",
    "heading_level_skipped": "WCAG 1.3.1 (Info and Relationships)",
    "empty_heading": "WCAG 1.3.1 (Empty Headings)",
    "missing_form_label": "WCAG 1.3.1 & 3.3.2 (Form Labels) & ת\"י 5568",
    "empty_button": "WCAG 4.1.2 (Name, Role, Value) & ת\"י 5568",
    "missing_alt": "WCAG 1.1.1 (Non-text Content) & ת\"י 5568",
    "empty_alt_content_image": "WCAG 1.1.1 (Non-text Content) & ת\"י 5568",
    "poor_alt": "WCAG 1.1.1 (Meaningful Text Alternative) & ת\"י 5568",
    "event_image_without_text": "WCAG 1.4.5 (Images of Text) & ת\"י 5568",
    "missing_a11y_statement": "חוק שוויון זכויות לאנשים עם מוגבלות (תקנה 35) & ת\"י 5568",
    "fake_a11y_statement_link": "חוק שוויון זכויות לאנשים עם מוגבלות (תקנה 35) & ת\"י 5568",
    "empty_link": "WCAG 2.4.4 & 4.1.2 (Accessible Name for Links) & ת\"י 5568",
    "vague_anchor_text": "WCAG 2.4.4 (Link Purpose) & ת\"י 5568",
    "missing_skip_link": "WCAG 2.4.1 (Bypass Blocks) & ת\"י 5568",
    "target_blank_no_warning": "WCAG 3.2.5 (Change on Request) & ת\"י 5568",
    "positive_tabindex": "WCAG 2.4.3 (Focus Order)",
    "zoom_disabled": "WCAG 1.4.4 (Resize Text - Level AA) & ת\"י 5568",
    "missing_main_landmark": "WCAG 2.4.1 (Bypass Blocks) & ת\"י 5568",
    "table_without_headers": "WCAG 1.3.1 (Table Relationships)",
    "audio_control": "WCAG 1.4.2 (Audio Control) & ת\"י 5568"
}

def calculate_scores(all_issues: list) -> tuple:
    penalties = {"critical": 14, "high": 7, "medium": 4, "low": 2}
    
    cat_deductions = {
        "links": 0,
        "images": 0,
        "a11y": 0,
        "seo": 0,
        "security": 0
    }
    
    a11y_deduction = 0
    tech_deduction = 0
    total_deduction = 0
    
    for iss in all_issues:
        sev = iss.get("severity", "medium")
        pen = penalties.get(sev, 4)
        cat = iss.get("category", "seo")
        cat_deductions[cat] = cat_deductions.get(cat, 0) + pen
        total_deduction += pen
        
        if cat == "a11y" or iss.get("is_a11y"):
            a11y_deduction += pen
        else:
            tech_deduction += pen
            
    total_score = max(0, min(100, 100 - total_deduction))
    a11y_score = max(0, min(100, 100 - a11y_deduction))
    tech_score = max(0, min(100, 100 - tech_deduction))
    
    cat_scores = {k: max(0, 100 - v) for k, v in cat_deductions.items()}
    cat_scores["a11y"] = a11y_score  # Force 100% sync
    
    return total_score, a11y_score, tech_score, cat_scores

SINGLETON_TYPES = {
    "missing_alt", "empty_alt_content_image", "poor_alt", 
    "event_image_without_text", "missing_a11y_statement", 
    "fake_a11y_statement_link", "empty_link", "missing_h1", 
    "multiple_h1", "missing_html_lang", "missing_main_landmark",
    "zoom_disabled", "missing_skip_link", "positive_tabindex",
    "table_without_headers", "audio_control", "target_blank_no_warning",
    "vague_anchor_text"
}

def build_todo_list(raw_results: dict) -> dict:
    all_issues = []
    seen_singleton_types = set()
    seen_issue_keys = set()
    
    def add_issue(iss, default_cat):
        iss_type = iss.get("type", "")
        if iss_type in SINGLETON_TYPES:
            if iss_type in seen_singleton_types:
                return
            seen_singleton_types.add(iss_type)
        else:
            dedup_key = (iss_type, iss.get("message", "")[:40])
            if dedup_key in seen_issue_keys:
                return
            seen_issue_keys.add(dedup_key)
        
        iss_copy = dict(iss)
        iss_copy["category"] = iss.get("category", default_cat)
        
        # Check if this issue is an accessibility requirement
        if iss_type in WCAG_MAP or iss_copy["category"] == "a11y":
            iss_copy["is_a11y"] = True
            iss_copy["wcag_standard"] = WCAG_MAP.get(iss_type, "תקן נגישות ת\"י 5568 / WCAG AA")
            
        all_issues.append(iss_copy)
        
    # 1. Process accessibility issues
    for iss in raw_results.get("a11y", {}).get("issues", []):
        add_issue(iss, "a11y")
        
    # 2. Process images issues
    for iss in raw_results.get("images", {}).get("issues", []):
        add_issue(iss, "images")
        
    # 3. Process links issues
    for iss in raw_results.get("links", {}).get("issues", []):
        add_issue(iss, "links")
        
    # 4. Process SEO issues
    for iss in raw_results.get("seo", {}).get("issues", []):
        add_issue(iss, "seo")
        
    # 5. Process security issues
    for iss in raw_results.get("security", {}).get("issues", []):
        add_issue(iss, "security")
        
    weight_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
    all_issues.sort(key=lambda x: weight_map.get(x.get("severity", "medium"), 3))
    
    category_labels = {
        "links": "🔗 קישורים",
        "images": "🖼️ תמונות ומדיה",
        "a11y": "♿ נגישות (ת\"י 5568)",
        "seo": "🔍 SEO ומבנה",
        "security": "🛡️ אבטחה ותוכן"
    }
    
    todos = []
    a11y_todos = []
    tech_todos = []
    task_id = 1
    
    for iss in all_issues:
        sev = iss.get("severity", "medium")
        cat = iss.get("category", "seo")
        is_a11y = iss.get("is_a11y", False) or cat == "a11y"
        
        est_time = "5-10 דק'"
        if sev == "critical":
            est_time = "10-20 דק'"
        elif sev == "low":
            est_time = "2-5 דק'"
            
        task = {
            "id": f"task-{task_id}",
            "priority": sev,
            "category": cat,
            "category_label": category_labels.get(cat, cat),
            "is_accessibility": is_a11y,
            "wcag_standard": iss.get("wcag_standard"),
            "title": iss.get("message"),
            "element": iss.get("element", ""),
            "recommendation": iss.get("recommendation", ""),
            "estimated_time": est_time,
            "completed": False
        }
        
        todos.append(task)
        if is_a11y:
            a11y_todos.append(task)
        else:
            tech_todos.append(task)
            
        task_id += 1
        
    overall_score, a11y_score, tech_score, category_scores = calculate_scores(all_issues)
    
    critical_count = sum(1 for t in todos if t["priority"] == "critical")
    high_count = sum(1 for t in todos if t["priority"] == "high")
    medium_count = sum(1 for t in todos if t["priority"] == "medium")
    low_count = sum(1 for t in todos if t["priority"] == "low")
    total_count = len(todos)
    a11y_count = len(a11y_todos)
    tech_count = len(tech_todos)
    
    if total_count == 0:
        readiness_status = "ready"
        verdict_title = "🎳 STRIKE! The Dude Abides — האתר קושר את כל החדר ביחד!"
        verdict_desc = "האתר עבר את כל חוקי הליגה, נקי לחלוטין מליקויים ומוכן למסירה ללקוח. אפילו וולטר סובצ'אק מרוצה!"
    elif critical_count > 0:
        readiness_status = "not_ready"
        verdict_title = "🛑 OVER THE LINE! Smokey, יש כאן עבירה על חוקי הליגה!"
        verdict_desc = f"נמצאו {total_count} תקלות ({a11y_count} נגישות, {tech_count} טכני), מתוכן {critical_count} קריטיות שחוסמות מסירה. 'This is not Vietnam, this is bowling, there are rules!'"
    elif high_count > 0:
        readiness_status = "needs_work"
        verdict_title = "🎳 SPARE! Mark it 8, Dude — נדרשים כמה תיקונים לפני הגמר"
        verdict_desc = f"נמצאו {total_count} משימות ({a11y_count} נגישות, {tech_count} טכני). קח שלוק של White Russian ותקן את המשימות המסומנות בכתום לפני מסירה."
    else:
        readiness_status = "minor_polish"
        verdict_title = "🟡 THE DUDE'S CASUAL GLANCE — נדרש רק ליטוש קל"
        verdict_desc = f"נמצאו {total_count} שיפורים קלים בלבד. האתר כמעט קושר את החדר ביחד ומוכן למסירה לאחר סבב קצרצר."
        
    return {
        "overall_score": overall_score,
        "a11y_score": a11y_score,
        "tech_score": tech_score,
        "category_scores": category_scores,
        "verdict": {
            "status": readiness_status,
            "title": verdict_title,
            "description": verdict_desc,
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "total_count": total_count,
            "a11y_count": a11y_count,
            "tech_count": tech_count
        },
        "todos": todos,
        "a11y_todos": a11y_todos,
        "tech_todos": tech_todos
    }
