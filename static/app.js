let currentAudit = null;
let currentFilter = 'all';
let currentDiscipline = 'all'; // 'all', 'a11y', 'tech'
let currentView = 'todo';
let linksFilter = 'all';
let complianceFilter = 'all'; // 'all', 'passed', 'failed'

// Initialize Lucide icons on load and URL input listener
document.addEventListener('DOMContentLoaded', () => {
    if (window.lucide) {
        window.lucide.createIcons();
    }
    const inputEl = document.getElementById('targetUrlInput');
    if (inputEl) {
        inputEl.addEventListener('input', () => {
            handleUrlInputChange(inputEl.value);
        });
    }
});

function showToast(message) {
    const toast = document.getElementById('toastNotification');
    const msgEl = document.getElementById('toastMessage');
    if (toast && msgEl) {
        msgEl.innerText = message;
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 2800);
    } else {
        alert(message);
    }
}

function handleUrlInputChange(val) {
    const banner = document.getElementById('subpathScopeBanner');
    const label = document.getElementById('detectedPathLabel');
    if (!banner || !label) return;
    try {
        let u = val.trim();
        if (u && !u.startsWith('http://') && !u.startsWith('https://')) {
            u = 'https://' + u;
        }
        const parsed = new URL(u);
        const p = parsed.pathname;
        if (p && p.length > 1 && p !== '/') {
            banner.classList.remove('hidden');
            label.innerText = p;
            return;
        }
    } catch (e) {}
    banner.classList.add('hidden');
}

function switchScanTab(mode) {
    const urlForm = document.getElementById('urlForm');
    const htmlForm = document.getElementById('htmlForm');
    const tabUrlBtn = document.getElementById('tabUrlBtn');
    const tabHtmlBtn = document.getElementById('tabHtmlBtn');

    if (mode === 'url') {
        urlForm.classList.remove('hidden');
        htmlForm.classList.add('hidden');
        tabUrlBtn.className = 'px-5 py-2 rounded-lg text-xs font-bold transition bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg';
        tabHtmlBtn.className = 'px-5 py-2 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition';
    } else {
        urlForm.classList.add('hidden');
        htmlForm.classList.remove('hidden');
        tabHtmlBtn.className = 'px-5 py-2 rounded-lg text-xs font-bold transition bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg';
        tabUrlBtn.className = 'px-5 py-2 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition';
    }
}

async function handleUrlSubmit(e) {
    e.preventDefault();
    const url = document.getElementById('targetUrlInput').value.trim();
    const checkLive = document.getElementById('checkLiveStatusBox').checked;
    if (!url) return;

    let scopePath = null;
    let excludeHeaderFooter = false;

    const limitBox = document.getElementById('limitToSubpathBox');
    const banner = document.getElementById('subpathScopeBanner');
    if (limitBox && limitBox.checked && !banner.classList.contains('hidden')) {
        try {
            let u = url;
            if (!u.startsWith('http://') && !u.startsWith('https://')) u = 'https://' + u;
            const parsed = new URL(u);
            scopePath = parsed.pathname;
        } catch (e) {}
        const excludeBox = document.getElementById('excludeHeaderFooterBox');
        if (excludeBox && excludeBox.checked) {
            excludeHeaderFooter = true;
        }
    }

    await executeAudit({ 
        url, 
        check_live: checkLive,
        scope_path: scopePath,
        exclude_header_footer: excludeHeaderFooter
    });
}

async function handleHtmlSubmit(e) {
    e.preventDefault();
    const html = document.getElementById('rawHtmlInput').value.trim();
    if (!html) return;

    await executeAudit({ html, check_live: true });
}

async function loadSampleDemo() {
    switchScanTab('html');
    showLoading(true, "קח שלוק של White Russian... טוען דוגמת אתר לבדיקה!");
    try {
        const res = await fetch('/api/sample-html');
        const data = await res.json();
        document.getElementById('rawHtmlInput').value = data.html;
        await executeAudit({ html: data.html, check_live: false });
    } catch (err) {
        showToast("שגיאה בטעינת דוגמה: " + err.message);
        showLoading(false);
    }
}

function showLoading(show, message = "The Dude מגלגל כדור במסלול...") {
    const loadingState = document.getElementById('loadingState');
    const resultsContainer = document.getElementById('resultsContainer');
    const statusText = document.getElementById('loadingStatusText');

    if (show) {
        loadingState.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        if (statusText) statusText.innerText = message;
    } else {
        loadingState.classList.add('hidden');
    }
}

async function executeAudit(payload) {
    showLoading(true, "The Dude מגלגל כדור במסלול... סורק קישורים, כרזות אירועים, תמונות ונגישות ת\"י 5568");
    try {
        const resp = await fetch('/api/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await resp.json();
        showLoading(false);

        if (!data.success) {
            showToast("שגיאה בביצוע הבדיקה: " + (data.error || "שגיאה לא ידועה"));
            return;
        }

        currentAudit = data;
        loadSavedTodoProgress();
        renderAuditResults(data);

        // Show print button
        document.getElementById('printBtn').classList.remove('hidden');
        document.getElementById('resultsContainer').classList.remove('hidden');

        // Scroll to results
        document.getElementById('resultsContainer').scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
        showLoading(false);
        showToast("שגיאת תקשורת עם השרת: " + err.message);
    }
}

function loadSavedTodoProgress() {
    if (!currentAudit) return;
    const storageKey = `launchready_todos_${currentAudit.domain || 'raw'}`;
    const saved = localStorage.getItem(storageKey);
    if (saved) {
        try {
            const completedIds = JSON.parse(saved);
            currentAudit.todos.forEach(t => {
                if (completedIds.includes(t.id)) {
                    t.completed = true;
                }
            });
        } catch (e) {}
    }
}

function saveTodoProgress() {
    if (!currentAudit) return;
    const storageKey = `launchready_todos_${currentAudit.domain || 'raw'}`;
    const completedIds = currentAudit.todos.filter(t => t.completed).map(t => t.id);
    localStorage.setItem(storageKey, JSON.stringify(completedIds));
}

function renderAuditResults(data) {
    const { overall_score, verdict, category_scores, raw_results, todos } = data;

    // 1. Overall Score Gauge
    const scoreValEl = document.getElementById('scoreValue');
    const gaugeEl = document.getElementById('scoreGauge');
    scoreValEl.innerText = overall_score;

    let gaugeColor = '#10b981'; // green
    if (overall_score < 60) {
        gaugeColor = '#f43f5e'; // red
    } else if (overall_score < 80) {
        gaugeColor = '#f59e0b'; // yellow/amber
    }
    gaugeEl.style.background = `conic-gradient(${gaugeColor} 0% ${overall_score}%, #1e293b ${overall_score}% 100%)`;

    // 2. Pillar Scores (Accessibility vs Technical)
    const a11yScore = data.a11y_score ?? 100;
    const techScore = data.tech_score ?? 100;

    if (document.getElementById('scoreA11yVal')) {
        document.getElementById('scoreA11yVal').innerText = a11yScore;
    }
    if (document.getElementById('scoreTechVal')) {
        document.getElementById('scoreTechVal').innerText = techScore;
    }
    if (document.getElementById('badgeA11yTasks')) {
        document.getElementById('badgeA11yTasks').innerText = data.a11y_todos ? data.a11y_todos.length : 0;
    }
    if (document.getElementById('badgeTechTasks')) {
        document.getElementById('badgeTechTasks').innerText = data.tech_todos ? data.tech_todos.length : 0;
    }
    if (document.getElementById('badgeAllTasks')) {
        document.getElementById('badgeAllTasks').innerText = data.todos ? data.todos.length : 0;
    }

    const a11yPill = document.getElementById('a11yStatusPill');
    if (a11yPill) {
        if (a11yScore >= 90) {
            a11yPill.innerText = '✅ עמידה בתקן ת"י 5568';
            a11yPill.className = 'text-[11px] text-emerald-400 font-bold block';
        } else if (a11yScore >= 60) {
            a11yPill.innerText = '⚠️ ליקויים הדורשים תיקון';
            a11yPill.className = 'text-[11px] text-amber-400 font-bold block';
        } else {
            a11yPill.innerText = '🚨 אי-עמידה בתקן החוקי';
            a11yPill.className = 'text-[11px] text-rose-400 font-bold block';
        }
    }

    // Verdict Title & Desc
    const verdictTitleEl = document.getElementById('verdictTitle');
    const verdictDescEl = document.getElementById('verdictDesc');
    verdictTitleEl.innerText = verdict.title;
    verdictDescEl.innerText = verdict.description;

    // 3. Meta details
    document.getElementById('metaTargetUrl').innerText = data.target_url;
    document.getElementById('metaLoadTime').innerText = `${data.load_time_ms} ms`;
    document.getElementById('metaPageSize').innerText = `${data.content_size_kb} KB`;
    document.getElementById('metaScanTime').innerText = data.scan_time;

    // 4. Category Scores & Stats
    // Links
    document.getElementById('catScoreLinks').innerText = category_scores.links ?? 100;
    document.getElementById('statBrokenLinks').innerText = raw_results.links.broken_links_count;
    document.getElementById('statTotalLinks').innerText = `${raw_results.links.total_links} סה"כ`;
    if (data.scope_path) {
        document.getElementById('linksSummaryText').innerText = 
            `🎯 נתיב ${data.scope_path} (הוחרגו ${data.out_of_scope_links_count || 0} קישורי אב)`;
    } else {
        document.getElementById('linksSummaryText').innerText = 
            raw_results.links.broken_links_count > 0 ? `⚠️ ${raw_results.links.broken_links_count} קישורים שבורים` : '✅ כל הקישורים תקינים';
    }

    // Images
    document.getElementById('catScoreImages').innerText = category_scores.images ?? 100;
    document.getElementById('statMissingAlt').innerText = raw_results.images.missing_alt_count;
    document.getElementById('statTotalImages').innerText = `${raw_results.images.total_images} סה"כ`;
    document.getElementById('imagesSummaryText').innerText = 
        raw_results.images.has_favicon ? '✅ Favicon קיים' : '⚠️ חסר Favicon בדפדפן';

    // Accessibility
    document.getElementById('catScoreA11y').innerText = category_scores.a11y ?? 100;
    const h1Count = raw_results.a11y.h1_count;
    const h1StatusEl = document.getElementById('statH1Status');
    if (h1Count === 1) {
        h1StatusEl.innerText = 'H1 תקין ויחיד';
        h1StatusEl.className = 'text-emerald-400';
    } else if (h1Count === 0) {
        h1StatusEl.innerText = 'חסר H1!';
        h1StatusEl.className = 'text-rose-400 font-bold';
    } else {
        h1StatusEl.innerText = `${h1Count} כותרות H1`;
        h1StatusEl.className = 'text-amber-400';
    }
    document.getElementById('a11ySummaryText').innerText = `שפת HTML: ${raw_results.a11y.html_lang}`;

    // SEO
    document.getElementById('catScoreSeo').innerText = category_scores.seo ?? 100;
    const robotsText = raw_results.seo.robots_meta || '';
    const robotsEl = document.getElementById('statRobotsStatus');
    if (robotsText.includes('noindex')) {
        robotsEl.innerText = '🚨 noindex חוסם!';
        robotsEl.className = 'text-rose-400 font-extrabold';
    } else {
        robotsEl.innerText = 'אינדוקס תקין';
        robotsEl.className = 'text-emerald-400';
    }
    document.getElementById('seoSummaryText').innerText = 
        raw_results.seo.title ? `כותרת: ${raw_results.seo.title.slice(0, 20)}...` : 'חסר Title!';

    // Security & Hygiene
    document.getElementById('catScoreSecurity').innerText = category_scores.security ?? 100;
    const httpsEl = document.getElementById('statHttpsStatus');
    if (raw_results.security.is_https) {
        httpsEl.innerText = 'HTTPS מאובטח';
        httpsEl.className = 'text-emerald-400';
    } else {
        httpsEl.innerText = 'HTTP לא מאובטח';
        httpsEl.className = 'text-rose-400 font-bold';
    }
    document.getElementById('securitySummaryText').innerText = 
        raw_results.security.found_lorem ? '🚨 נמצא טקסט Lorem Ipsum!' : 'מלל נקי מדמה';

    // Badge count for TODO
    document.getElementById('badgeTodoCount').innerText = todos.length;

    // Accessibility Compliance Data & Counters
    const compData = data.a11y_compliance || data.raw_results?.a11y || {};
    let compChecks = compData.all_checks || compData.compliance_checks || [];
    let passedChecks = compData.passed_checks || compChecks.filter(c => c.status === 'passed');
    let failedChecks = compData.failed_checks || compChecks.filter(c => c.status === 'failed');

    // Robust fallback if checks were not pre-calculated
    if (compChecks.length === 0 && data.raw_results?.a11y) {
        const a11y = data.raw_results.a11y;
        if (a11y.html_lang && a11y.html_lang !== 'חסר') {
            passedChecks.push({ id: 'wcag_lang', name: 'הגדרת שפת מסמך ראשית', standard: 'WCAG 3.1.1 (Level A) & ת"י 5568', status: 'passed', details: `שפת הדף הראשית מוגדרת כראוי בתגית <html>: '${a11y.html_lang}'.` });
        }
        if (a11y.h1_count === 1) {
            passedChecks.push({ id: 'wcag_h1', name: 'כותרת ראשית <h1> יחידה', standard: 'WCAG 1.3.1 & 2.4.6 & ת"י 5568', status: 'passed', details: 'קיימת כותרת H1 ראשית אחת ויחידה.' });
        }
        if (a11y.unlabeled_inputs_count === 0) {
            passedChecks.push({ id: 'wcag_form_labels', name: 'תוויות נגישות לשדות טופס (<label>)', standard: 'WCAG 1.3.1 & 3.3.2 & ת"י 5568', status: 'passed', details: 'כל שדות הטופס כוללים תוויות נגישות.' });
        }
        if (a11y.landmarks && a11y.landmarks.has_main) {
            passedChecks.push({ id: 'wcag_main_landmark', name: 'אזור תוכן מרכזי סמנטי (<main>)', standard: 'WCAG 2.4.1 (Bypass Blocks)', status: 'passed', details: 'קיים אזור <main> תקני.' });
        }
        compChecks = [...passedChecks];
    }

    const totalChecksCount = compChecks.length || 16;
    if (document.getElementById('badgeA11yCompliance')) {
        document.getElementById('badgeA11yCompliance').innerText = `${passedChecks.length} תקין`;
    }
    if (document.getElementById('statA11yPassedRatio')) {
        document.getElementById('statA11yPassedRatio').innerText = `${passedChecks.length}/${totalChecksCount} תקין`;
    }
    if (document.getElementById('statCompliancePassed')) {
        document.getElementById('statCompliancePassed').innerText = passedChecks.length;
    }
    if (document.getElementById('statComplianceFailed')) {
        document.getElementById('statComplianceFailed').innerText = failedChecks.length;
    }
    if (document.getElementById('countCompAll')) {
        document.getElementById('countCompAll').innerText = compChecks.length;
    }
    if (document.getElementById('countCompPassed')) {
        document.getElementById('countCompPassed').innerText = passedChecks.length;
    }
    if (document.getElementById('countCompFailed')) {
        document.getElementById('countCompFailed').innerText = failedChecks.length;
    }
    if (document.getElementById('a11yPassedBannerText')) {
        document.getElementById('a11yPassedBannerText').innerText = 
            `${passedChecks.length} מתוך ${totalChecksCount} סעיפי תקן נבדקו ונמצאו תקינים לחלוטין.`;
    }

    if (document.getElementById('badgeA11yPassedBtn')) {
        document.getElementById('badgeA11yPassedBtn').innerText = passedChecks.length;
    }
    if (document.getElementById('badgeTodoPassedCount')) {
        document.getElementById('badgeTodoPassedCount').innerText = `${passedChecks.length} סעיפים תקינים`;
    }

    // Render Subcomponents
    renderTodoPassedA11yList(passedChecks);
    renderTodoList();
    renderComplianceChecklist();
    renderLinksTable();
    renderImagesTable();
    renderPreviews();

    if (window.lucide) window.lucide.createIcons();
}

let isPassedA11yCollapsed = false;
function togglePassedA11yCollapse() {
    isPassedA11yCollapsed = !isPassedA11yCollapsed;
    const list = document.getElementById('todoPassedA11yList');
    const label = document.getElementById('labelTogglePassedA11y');
    const icon = document.getElementById('iconTogglePassedA11y');
    if (list) {
        if (isPassedA11yCollapsed) {
            list.classList.add('hidden');
            if (label) label.innerText = 'הצג סעיפים';
        } else {
            list.classList.remove('hidden');
            if (label) label.innerText = 'הסתר סעיפים';
        }
    }
}

function renderTodoPassedA11yList(passedChecks) {
    const el = document.getElementById('todoPassedA11yList');
    if (!el) return;
    el.innerHTML = '';

    if (!passedChecks || !passedChecks.length) {
        el.innerHTML = '<div class="text-xs text-slate-400 p-3 col-span-2 text-center bg-black/40 rounded-xl">טרם אותרו סעיפים תקינים בדף זה.</div>';
        return;
    }

    passedChecks.forEach(c => {
        const div = document.createElement('div');
        div.className = 'cockpit-card rounded-xl p-3.5 border border-emerald-500/30 bg-black/60 flex items-start gap-3 text-right hover:border-emerald-400/50 transition';
        div.innerHTML = `
            <div class="w-6 h-6 rounded-md bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center shrink-0 mt-0.5 text-emerald-400 font-bold">
                <i data-lucide="check" class="w-3.5 h-3.5"></i>
            </div>
            <div class="flex-1 space-y-1">
                <div class="flex items-center justify-between gap-1 flex-wrap">
                    <span class="text-xs font-bold text-white">${escapeHtml(c.name)}</span>
                    <span class="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-500/30">${escapeHtml(c.standard)}</span>
                </div>
                <p class="text-[11px] text-slate-300 leading-relaxed">${escapeHtml(c.details)}</p>
            </div>
        `;
        el.appendChild(div);
    });

    if (window.lucide) window.lucide.createIcons();
}

function setDisciplineFilter(mode) {
    currentDiscipline = mode;
    const btnA11y = document.getElementById('discBtnA11y');
    const btnA11yPassed = document.getElementById('discBtnA11yPassed');
    const btnTech = document.getElementById('discBtnTech');
    const btnAll = document.getElementById('discBtnAll');

    const defaultClass = 'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 bg-[#2a1a10] text-amber-200 hover:text-white border border-transparent';

    if (btnA11y && btnTech && btnAll) {
        btnA11y.className = defaultClass;
        if (btnA11yPassed) btnA11yPassed.className = defaultClass;
        btnTech.className = defaultClass;
        btnAll.className = defaultClass;

        if (mode === 'a11y') {
            btnA11y.className = 'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 bg-emerald-600 text-white shadow-lg shadow-emerald-900/40 border border-emerald-400/40';
        } else if (mode === 'a11y_passed') {
            if (btnA11yPassed) btnA11yPassed.className = 'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-900/40 border border-emerald-400/40';
        } else if (mode === 'tech') {
            btnTech.className = 'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 bg-gradient-to-r from-amber-600 to-amber-700 text-white shadow-lg shadow-amber-900/40 border border-amber-400/40';
        } else {
            btnAll.className = 'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 bg-gradient-to-r from-amber-600 to-orange-600 text-white shadow-lg border border-amber-400/40';
        }
    }

    // Toggle visibility of the passed accessibility box based on discipline
    const passedSec = document.getElementById('todoPassedA11ySection');
    if (passedSec) {
        if (mode === 'tech') {
            passedSec.classList.add('hidden');
        } else {
            passedSec.classList.remove('hidden');
        }
    }

    renderTodoList();
}

function renderTodoList() {
    const listEl = document.getElementById('todoListItems');
    listEl.innerHTML = '';

    if (currentDiscipline === 'a11y_passed') {
        listEl.innerHTML = `
            <div class="cockpit-card rounded-2xl p-6 text-center text-emerald-300 bg-emerald-950/20 border border-emerald-500/35 text-xs">
                כל הסעיפים התקינים בנגישות מפורטים בתיבה הירוקה למעלה. למעבר לרשימת הליקויים לתיקון, לחץ על <strong>"📜 עבירות נגישות לתיקון"</strong>.
            </div>
        `;
        updateTodoProgress();
        return;
    }

    if (!currentAudit || !currentAudit.todos.length) {
        listEl.innerHTML = `
            <div class="cockpit-card rounded-2xl p-10 text-center text-amber-200/80">
                <span class="text-4xl block mb-3 animate-bounce">🎳</span>
                <h4 class="text-base font-bold text-white font-lebowski">STRIKE! ALL PINS DOWN // THE DUDE ABIDES</h4>
                <p class="text-xs text-amber-300/70 mt-1">האתר קושר את כל החדר ביחד, נקי לחלוטין מליקויים ומוכן למסירה ללקוח.</p>
            </div>
        `;
        updateTodoProgress();
        if (window.lucide) window.lucide.createIcons();
        return;
    }

    const filtered = currentAudit.todos.filter(t => {
        if (currentDiscipline === 'a11y' && !t.is_accessibility) return false;
        if (currentDiscipline === 'tech' && t.is_accessibility) return false;
        if (currentFilter !== 'all' && t.priority !== currentFilter) return false;
        return true;
    });

    if (filtered.length === 0) {
        listEl.innerHTML = `
            <div class="cockpit-card rounded-2xl p-8 text-center text-amber-200/60 text-xs">
                לא נמצאו משימות מתאימות לסינון שנבחר.
            </div>
        `;
        updateTodoProgress();
        return;
    }

    filtered.forEach(item => {
        const card = document.createElement('div');
        const isCompleted = item.completed;

        const sevColors = {
            critical: { badge: 'bg-rose-950/80 text-rose-300 border-rose-500/40', label: '🛑 עבירת ליגה קריטית', stripe: 'border-r-4 border-r-rose-500' },
            high: { badge: 'bg-amber-950/80 text-amber-300 border-amber-500/40', label: '🟠 חשוב מאוד', stripe: 'border-r-4 border-r-amber-500' },
            medium: { badge: 'bg-yellow-950/80 text-yellow-300 border-yellow-500/40', label: '🟡 מומלץ לשיפור', stripe: 'border-r-4 border-r-yellow-500' },
            low: { badge: 'bg-[#2a1a10] text-amber-300/80 border-amber-700/40', label: '🟢 ליטוש קל', stripe: 'border-r-4 border-r-amber-600' }
        };
        const sevInfo = sevColors[item.priority] || sevColors.medium;
        const borderStripe = item.is_accessibility ? 'border-r-4 border-r-emerald-400 bg-emerald-950/15' : sevInfo.stripe;

        card.className = `cockpit-card rounded-2xl p-5 border transition ${borderStripe} ${isCompleted ? 'opacity-40 line-through' : ''}`;
        card.innerHTML = `
            <div class="flex items-start gap-4">
                <input 
                    type="checkbox" 
                    ${isCompleted ? 'checked' : ''} 
                    onchange="toggleTodoItem('${item.id}')"
                    class="custom-checkbox mt-1"
                />
                <div class="flex-1 space-y-2.5 text-right">
                    <div class="flex flex-wrap items-center justify-between gap-2">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-xs font-bold px-2.5 py-0.5 rounded-lg border ${sevInfo.badge}">${sevInfo.label}</span>
                            ${item.is_accessibility ? `
                                <span class="text-xs font-bold px-2.5 py-0.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono">
                                    ♿ ${escapeHtml(item.wcag_standard || 'תקן ת"י 5568 / WCAG AA')}
                                </span>
                            ` : `
                                <span class="text-xs px-2.5 py-0.5 rounded-lg bg-slate-800 text-slate-400">${item.category_label}</span>
                            `}
                        </div>
                        <span class="text-[11px] text-slate-500 font-mono">TIME: ~${item.estimated_time}</span>
                    </div>

                    <h4 class="text-sm sm:text-base font-bold text-white">
                        ${escapeHtml(item.title)}
                    </h4>

                    ${item.element ? `
                        <div class="bg-black/80 rounded-xl p-3 font-mono text-xs text-cyan-300 border border-white/10 overflow-x-auto shadow-inner" dir="ltr">
                            <code>${escapeHtml(item.element)}</code>
                        </div>
                    ` : ''}

                    <div class="${item.is_accessibility ? 'bg-emerald-950/30 border-emerald-500/25 text-emerald-200' : 'bg-cyan-950/30 border-cyan-500/25 text-cyan-200'} border rounded-xl p-3 text-xs leading-relaxed">
                        <strong class="${item.is_accessibility ? 'text-emerald-400' : 'text-cyan-400'} block mb-1">💡 הנחיית תיקון מדויקת:</strong>
                        <span>${escapeHtml(item.recommendation)}</span>
                    </div>
                </div>
            </div>
        `;
        listEl.appendChild(card);
    });

    updateTodoProgress();
}

function toggleTodoItem(id) {
    if (!currentAudit) return;
    const task = currentAudit.todos.find(t => t.id === id);
    if (task) {
        task.completed = !task.completed;
        saveTodoProgress();
        renderTodoList();
    }
}

function updateTodoProgress() {
    if (!currentAudit) return;
    const total = currentAudit.todos.length;
    const completed = currentAudit.todos.filter(t => t.completed).length;
    const pct = total > 0 ? Math.round((completed / total) * 100) : 100;

    const barEl = document.getElementById('todoProgressBar');
    const textEl = document.getElementById('todoProgressText');

    if (barEl) barEl.style.width = `${pct}%`;
    if (textEl) textEl.innerText = `${completed} / ${total} הושלמו (${pct}%)`;
}

function filterTodos(priority) {
    currentFilter = priority;
    document.querySelectorAll('.todo-filter-btn').forEach(btn => {
        if (btn.getAttribute('data-filter') === priority) {
            btn.className = 'todo-filter-btn px-3 py-1 rounded-lg text-xs font-bold bg-white/20 text-white border border-white/20';
        } else {
            btn.className = 'todo-filter-btn px-3 py-1 rounded-lg text-xs font-bold bg-slate-900 text-slate-400 hover:bg-slate-800 border border-transparent';
        }
    });
    renderTodoList();
}

function renderComplianceChecklist() {
    const listEl = document.getElementById('complianceChecklistItems');
    if (!listEl) return;
    listEl.innerHTML = '';

    if (!currentAudit) return;

    const compData = currentAudit.a11y_compliance || currentAudit.raw_results?.a11y || {};
    let checks = compData.all_checks || compData.compliance_checks || [];

    if (checks.length === 0 && currentAudit.raw_results?.a11y) {
        const a11y = currentAudit.raw_results.a11y;
        if (a11y.html_lang && a11y.html_lang !== 'חסר') {
            checks.push({ id: 'wcag_lang', name: 'הגדרת שפת מסמך ראשית', standard: 'WCAG 3.1.1 (Level A) & ת"י 5568', status: 'passed', details: `שפת הדף הראשית מוגדרת כראוי בתגית <html>: '${a11y.html_lang}'.` });
        }
        if (a11y.h1_count === 1) {
            checks.push({ id: 'wcag_h1', name: 'כותרת ראשית <h1> יחידה', standard: 'WCAG 1.3.1 & 2.4.6 & ת"י 5568', status: 'passed', details: 'קיימת כותרת H1 ראשית אחת ויחידה.' });
        } else {
            checks.push({ id: 'wcag_h1', name: 'כותרת ראשית <h1> יחידה', standard: 'WCAG 1.3.1 & 2.4.6 & ת"י 5568', status: 'failed', details: 'לא נמצאה כותרת ראשית H1 אחת ויחידה בדף.' });
        }
        if (a11y.unlabeled_inputs_count === 0) {
            checks.push({ id: 'wcag_form_labels', name: 'תוויות נגישות לשדות טופס (<label>)', standard: 'WCAG 1.3.1 & 3.3.2 & ת"י 5568', status: 'passed', details: 'כל שדות הטופס כוללים תוויות נגישות.' });
        }
        if (a11y.landmarks && a11y.landmarks.has_main) {
            checks.push({ id: 'wcag_main_landmark', name: 'אזור תוכן מרכזי סמנטי (<main>)', standard: 'WCAG 2.4.1 (Bypass Blocks)', status: 'passed', details: 'קיים אזור <main> תקני.' });
        }
    }

    const filtered = checks.filter(c => {
        if (complianceFilter === 'passed') return c.status === 'passed';
        if (complianceFilter === 'failed') return c.status === 'failed';
        return true;
    });

    if (filtered.length === 0) {
        listEl.innerHTML = `
            <div class="cockpit-card rounded-2xl p-8 text-center text-slate-400 text-xs">
                לא נמצאו סעיפים התואמים לסינון שנבחר.
            </div>
        `;
        return;
    }

    filtered.forEach(c => {
        const card = document.createElement('div');
        const isPassed = c.status === 'passed';

        if (isPassed) {
            card.className = 'cockpit-card rounded-xl p-5 border border-emerald-500/25 bg-emerald-950/10 border-r-4 border-r-emerald-500 space-y-2 transition hover:border-emerald-500/40';
            card.innerHTML = `
                <div class="flex items-start gap-3.5">
                    <div class="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center shrink-0 mt-0.5">
                        <i data-lucide="check" class="w-5 h-5 text-emerald-400"></i>
                    </div>
                    <div class="flex-1 space-y-2 text-right">
                        <div class="flex flex-wrap items-center justify-between gap-2">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="text-xs font-bold px-2.5 py-0.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                                    ✅ תקין ועומד בתקן
                                </span>
                                <span class="text-xs font-mono px-2 py-0.5 rounded-lg bg-slate-900 text-slate-300 border border-white/10">
                                    ${escapeHtml(c.standard)}
                                </span>
                            </div>
                            <span class="text-[11px] font-mono text-emerald-400/80">VERIFIED COMPLIANT</span>
                        </div>
                        <h4 class="text-sm sm:text-base font-bold text-white">
                            ${escapeHtml(c.name)}
                        </h4>
                        <p class="text-xs text-slate-300 leading-relaxed bg-black/40 p-3 rounded-xl border border-white/5">
                            ${escapeHtml(c.details)}
                        </p>
                    </div>
                </div>
            `;
        } else {
            card.className = 'cockpit-card rounded-xl p-5 border border-rose-500/30 bg-rose-950/15 border-r-4 border-r-rose-500 space-y-2 transition hover:border-rose-500/50';
            card.innerHTML = `
                <div class="flex items-start gap-3.5">
                    <div class="w-8 h-8 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center shrink-0 mt-0.5">
                        <i data-lucide="alert-triangle" class="w-5 h-5 text-rose-400"></i>
                    </div>
                    <div class="flex-1 space-y-2 text-right">
                        <div class="flex flex-wrap items-center justify-between gap-2">
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="text-xs font-bold px-2.5 py-0.5 rounded-lg bg-rose-500/20 text-rose-300 border border-rose-500/40">
                                    ⚠️ ליקוי - אי עמידה בתקן
                                </span>
                                <span class="text-xs font-mono px-2 py-0.5 rounded-lg bg-slate-900 text-slate-300 border border-white/10">
                                    ${escapeHtml(c.standard)}
                                </span>
                            </div>
                            <button onclick="jumpToTodo()" class="text-[11px] px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 font-bold border border-rose-500/40 transition flex items-center gap-1">
                                <span>עבור למשימת תיקון ב-TODO</span>
                                <i data-lucide="arrow-left" class="w-3 h-3"></i>
                            </button>
                        </div>
                        <h4 class="text-sm sm:text-base font-bold text-white">
                            ${escapeHtml(c.name)}
                        </h4>
                        <p class="text-xs text-rose-200/90 leading-relaxed bg-black/40 p-3 rounded-xl border border-rose-500/10">
                            ${escapeHtml(c.details)}
                        </p>
                    </div>
                </div>
            `;
        }

        listEl.appendChild(card);
    });

    if (window.lucide) window.lucide.createIcons();
}

function filterComplianceView(mode) {
    complianceFilter = mode;
    const btnAll = document.getElementById('compFilterAll');
    const btnPassed = document.getElementById('compFilterPassed');
    const btnFailed = document.getElementById('compFilterFailed');

    if (btnAll && btnPassed && btnFailed) {
        btnAll.className = mode === 'all' 
            ? 'px-3 py-1.5 rounded-lg text-xs font-bold bg-white/20 text-white' 
            : 'px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-900 text-slate-400 hover:bg-slate-800';
        btnPassed.className = mode === 'passed'
            ? 'px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 text-white shadow-md'
            : 'px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-950/40 text-emerald-400 hover:bg-emerald-950/70 border border-emerald-500/30';
        btnFailed.className = mode === 'failed'
            ? 'px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-600 text-white shadow-md'
            : 'px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-950/40 text-rose-400 hover:bg-rose-950/70 border border-rose-500/30';
    }
    renderComplianceChecklist();
}

function jumpToTodo() {
    switchViewTab('todo');
    setDisciplineFilter('a11y');
}

function renderLinksTable() {
    const tbody = document.getElementById('linksTableBody');
    tbody.innerHTML = '';
    if (!currentAudit) return;

    const links = currentAudit.raw_results.links.links || [];
    const filtered = links.filter(l => {
        if (linksFilter === 'broken') return l.status_ok === false || (l.issues && l.issues.length > 0);
        if (linksFilter === 'in_scope') return l.is_in_scope !== false;
        if (linksFilter === 'out_of_scope') return l.is_in_scope === false;
        return true;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500 font-sans">לא נמצאו קישורים תואמים</td></tr>`;
        return;
    }

    filtered.forEach((l, idx) => {
        const tr = document.createElement('tr');
        const isBroken = l.status_ok === false || (l.issues && l.issues.some(i => i.includes('שבור') || i.includes('ריק')));
        tr.className = isBroken ? 'bg-rose-950/20 text-rose-300' : 'hover:bg-white/[0.02]';

        let statusBadge = '<span class="px-2 py-0.5 rounded bg-slate-800 text-slate-400">לא נבדק</span>';
        if (l.is_in_scope === false) {
            statusBadge = '<span class="px-2 py-0.5 rounded bg-slate-800 text-slate-500">הוחרג (אתר אב)</span>';
        } else if (l.status_code) {
            if (l.status_ok) {
                statusBadge = `<span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-bold">${l.status_code} OK</span>`;
            } else {
                statusBadge = `<span class="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-bold">${l.status_code || 'Error'}</span>`;
            }
        }

        tr.innerHTML = `
            <td class="p-3 text-slate-500">${idx + 1}</td>
            <td class="p-3 font-sans text-slate-200">${escapeHtml(l.text || '(ללא טקסט)')}</td>
            <td class="p-3 max-w-xs truncate" title="${escapeHtml(l.url || l.raw_href || '')}">
                <a href="${escapeHtml(l.url || l.raw_href || '#')}" target="_blank" class="hover:underline text-cyan-400">${escapeHtml(l.url || l.raw_href || '')}</a>
            </td>
            <td class="p-3"><span class="px-1.5 py-0.5 rounded bg-black/60 text-[10px] uppercase">${l.type}</span></td>
            <td class="p-3">${statusBadge}</td>
            <td class="p-3 font-sans text-xs text-rose-400">${l.issues ? l.issues.join(', ') : (l.scope_note || '')}</td>
        `;
        tbody.appendChild(tr);
    });
}

function filterLinksTable(mode) {
    linksFilter = mode;
    renderLinksTable();
}

function renderImagesTable() {
    const tbody = document.getElementById('imagesTableBody');
    tbody.innerHTML = '';
    if (!currentAudit) return;

    const images = currentAudit.raw_results.images.images || [];
    if (images.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500 font-sans">לא נמצאו תמונות בדף</td></tr>`;
        return;
    }

    images.forEach((img, idx) => {
        const tr = document.createElement('tr');
        const hasIssue = img.issues && img.issues.length > 0;
        tr.className = hasIssue ? 'bg-amber-950/15' : 'hover:bg-white/[0.02]';

        let altDisplay = '';
        if (img.alt === null || img.alt === undefined) {
            altDisplay = '<span class="text-rose-400 font-bold block">❌ חסר Alt לחלוטין!</span>';
        } else if (img.alt.trim() === '') {
            if (img.is_decorative) {
                altDisplay = '<span class="text-slate-500 italic block">דקורטיבי (alt ריק)</span>';
            } else {
                altDisplay = '<span class="text-rose-400 font-bold block">❌ alt ריק בתמונת תוכן!</span>';
            }
        } else {
            altDisplay = `<span class="text-slate-300 block">"${escapeHtml(img.alt)}"</span>`;
        }

        const flyerBadge = img.is_event_flyer 
            ? '<span class="inline-block mt-1 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-bold border border-amber-500/30">📢 כרזת אירוע/מבצע</span>' 
            : '';

        const issuesHtml = img.issues && img.issues.length 
            ? img.issues.map(iss => `<span class="inline-block my-0.5 px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-500/30 text-[11px]">${escapeHtml(iss)}</span>`).join('<br>') 
            : '<span class="text-emerald-400 text-xs">תקין</span>';

        tr.innerHTML = `
            <td class="p-3 text-slate-500">${idx + 1}</td>
            <td class="p-3 max-w-xs truncate text-cyan-400" title="${escapeHtml(img.full_url || img.src)}">
                <a href="${escapeHtml(img.full_url || img.src)}" target="_blank" class="hover:underline">${escapeHtml(img.src)}</a>
                ${flyerBadge}
            </td>
            <td class="p-3 font-sans">
                ${altDisplay}
            </td>
            <td class="p-3 text-slate-400 font-mono">
                ${img.width && img.height ? `${img.width}x${img.height}` : '<span class="text-amber-400">לא הוגדר</span>'}
            </td>
            <td class="p-3 text-slate-400 font-mono">
                ${img.status_code ? (img.status_ok ? `<span class="text-emerald-400 font-bold">${img.status_code}</span>` : `<span class="text-rose-400 font-bold">${img.status_code}</span>`) : '-'}
                ${img.size_kb ? ` (${img.size_kb} KB)` : ''}
            </td>
            <td class="p-3 font-sans text-xs">${issuesHtml}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderPreviews() {
    if (!currentAudit) return;
    const seo = currentAudit.raw_results?.seo || currentAudit.seo || {};
    const domain = currentAudit.domain || '';

    // Google SERP
    document.getElementById('previewSerpDomain').innerText = domain || 'example.com';
    document.getElementById('previewSerpTitle').innerText = seo.title || 'כותרת הדף (חסרה תגית Title)';
    document.getElementById('previewSerpDesc').innerText = seo.description || 'תיאור הדף (חסרה תגית meta description). גוגל יציג קטעים אקראיים מתוך תוכן האתר.';

    // OpenGraph
    const og = seo.open_graph || {};
    document.getElementById('previewOgDomain').innerText = (domain || 'EXAMPLE.COM').toUpperCase();
    document.getElementById('previewOgTitle').innerText = og.title || seo.title || 'כותרת השיתוף (חסר og:title)';
    document.getElementById('previewOgDesc').innerText = og.description || seo.description || 'תיאור השיתוף (חסר og:description)';

    const imgEl = document.getElementById('previewOgImg');
    const placeholderEl = document.getElementById('previewOgImgPlaceholder');
    if (og.image) {
        imgEl.src = og.image;
        imgEl.classList.remove('hidden');
        placeholderEl.classList.add('hidden');
    } else {
        imgEl.classList.add('hidden');
        placeholderEl.classList.remove('hidden');
    }
}

function switchViewTab(tab) {
    currentView = tab;
    const tabs = ['todo', 'a11yCompliance', 'links', 'images', 'preview'];
    tabs.forEach(t => {
        const btn = document.getElementById(`viewTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
        const panel = document.getElementById(`panel${t.charAt(0).toUpperCase() + t.slice(1)}`);
        if (btn && panel) {
            if (t === tab) {
                btn.className = 'px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-amber-600 to-amber-700 text-white flex items-center gap-2 shadow-lg shadow-amber-900/40 transition';
                panel.classList.remove('hidden');
            } else {
                btn.className = 'px-4 py-2 rounded-xl text-xs font-bold text-amber-200/70 hover:text-white flex items-center gap-2 transition';
                panel.classList.add('hidden');
            }
        }
    });

    if (window.lucide) window.lucide.createIcons();
}

function copyA11yComplianceReport() {
    if (!currentAudit) return;
    const compData = currentAudit.a11y_compliance || currentAudit.raw_results?.a11y || {};
    const checks = compData.all_checks || compData.compliance_checks || [];
    const passed = compData.passed_checks || checks.filter(c => c.status === 'passed');

    if (!passed.length) {
        showToast("לא נמצאו סעיפים תקינים להעתקה.");
        return;
    }

    let text = `✅ דוח עמידה בסעיפי נגישות תקינים (תקן ישראלי ת"י 5568 / WCAG 2.1 AA)\n`;
    text += `כתובת האתר: ${currentAudit.target_url}\n`;
    text += `ציון עמידה בנגישות: ${currentAudit.a11y_score}/100\n`;
    text += `תאריך בדיקה: ${currentAudit.scan_time}\n`;
    text += `סה"כ סעיפים שנבדקו ונמצאו תקינים: ${passed.length} מתוך ${checks.length}\n`;
    text += `הערה: סעיפים אלו נבדקו בקוד המקור ונמצאו תואמים לדרישות התקן (מוכן להצהרת נגישות).\n`;
    text += `==================================================\n\n`;

    passed.forEach((c, i) => {
        text += `${i + 1}. [V תקין] ${c.name}\n`;
        text += `   תקן רשמי: ${c.standard}\n`;
        text += `   פירוט בדיקה: ${c.details}\n\n`;
    });

    navigator.clipboard.writeText(text).then(() => {
        showToast("📋 רשימת הסעיפים התקינים (להצהרת נגישות) הועתקה ללוח בהצלחה!");
    }).catch(err => alert("שגיאה בהעתקה: " + err));
}

function copyA11yFullReport() {
    if (!currentAudit) return;
    const compData = currentAudit.a11y_compliance || currentAudit.raw_results?.a11y || {};
    const checks = compData.all_checks || compData.compliance_checks || [];
    const passed = compData.passed_checks || checks.filter(c => c.status === 'passed');
    const todos = currentAudit.a11y_todos || [];

    let text = `♿ דוח ביקורת נגישות מקיף (תקן ישראלי ת"י 5568 / WCAG 2.1 AA)\n`;
    text += `כתובת האתר: ${currentAudit.target_url}\n`;
    text += `ציון עמידה בנגישות: ${currentAudit.a11y_score}/100\n`;
    text += `תאריך בדיקה: ${currentAudit.scan_time}\n`;
    text += `סטטוס כללי: ${passed.length} סעיפים עברו בהצלחה | ${todos.length} ליקויים לתיקון\n`;
    text += `==================================================\n\n`;

    text += `--- חלק א': מה נבדק ונמצא תקין ועומד בתקן (${passed.length} סעיפים) ---\n`;
    passed.forEach((c, i) => {
        text += `${i + 1}. [V תקין] ${c.name} (${c.standard})\n`;
        text += `   פירוט: ${c.details}\n\n`;
    });

    text += `--- חלק ב': ליקויי נגישות ומשימות לתיקון (${todos.length} משימות) ---\n`;
    if (todos.length) {
        todos.forEach((t, i) => {
            const mark = t.completed ? '[V תוקן]' : '[ ]';
            text += `${i + 1}. ${mark} ${t.title}\n`;
            text += `   סעיף תקן: ${t.wcag_standard || 'ת"י 5568 / WCAG AA'}\n`;
            text += `   דרגת חומרה: ${t.priority.toUpperCase()}\n`;
            if (t.element) text += `   אלמנט: ${t.element}\n`;
            text += `   הנחיית תיקון: ${t.recommendation}\n\n`;
        });
    } else {
        text += `לא נמצאו ליקויים פתוחים! האתר עומד במלואו בתקן.\n\n`;
    }

    navigator.clipboard.writeText(text).then(() => {
        showToast("📋 דוח נגישות מלא (תקינים + ליקויים) הועתק ללוח בהצלחה!");
    }).catch(err => alert("שגיאה בהעתקה: " + err));
}

function copyA11yReport() {
    copyA11yFullReport();
}

function copyTechReport() {
    if (!currentAudit || !currentAudit.tech_todos || !currentAudit.tech_todos.length) {
        showToast("אין תקלות טכניות ברשימה!");
        return;
    }
    let text = `🛠️ דוח תקלות טכניות, קישורים, תמונות ו-SEO\n`;
    text += `כתובת האתר: ${currentAudit.target_url}\n`;
    text += `ציון איכות טכנית: ${currentAudit.tech_score}/100\n`;
    text += `תאריך בדיקה: ${currentAudit.scan_time}\n`;
    text += `סה"כ תקלות לתיקון: ${currentAudit.tech_todos.length}\n`;
    text += `--------------------------------------------------\n\n`;

    currentAudit.tech_todos.forEach((t, i) => {
        const mark = t.completed ? '[V תוקן]' : '[ ]';
        text += `${i + 1}. ${mark} ${t.title} (${t.category_label})\n`;
        text += `   דרגת חומרה: ${t.priority.toUpperCase()}\n`;
        if (t.element) text += `   אלמנט: ${t.element}\n`;
        text += `   הנחיית תיקון: ${t.recommendation}\n\n`;
    });

    navigator.clipboard.writeText(text).then(() => {
        showToast("📋 דוח התקלות הטכניות הועתק ללוח בהצלחה!");
    }).catch(err => alert("שגיאה בהעתקה: " + err));
}

function copyTodoList() {
    if (!currentAudit || !currentAudit.todos.length) {
        showToast("אין משימות להעתקה.");
        return;
    }

    let text = `📋 דוח משימות לתיקון לפני מסירת אתר (${currentAudit.target_url})\n`;
    text += `ציון מוכנות נוכחי: ${currentAudit.overall_score}/100\n`;
    text += `ציון נגישות: ${currentAudit.a11y_score}/100 | ציון טכני: ${currentAudit.tech_score}/100\n`;
    text += `--------------------------------------------------\n\n`;

    currentAudit.todos.forEach((t, i) => {
        const mark = t.completed ? '[V הושלם]' : '[ ]';
        text += `${i + 1}. ${mark} ${t.title} (${t.category_label} | ${t.priority.toUpperCase()})\n`;
        if (t.wcag_standard) text += `   תקן: ${t.wcag_standard}\n`;
        if (t.element) text += `   אלמנט: ${t.element}\n`;
        text += `   הנחיה לתיקון: ${t.recommendation}\n\n`;
    });

    navigator.clipboard.writeText(text).then(() => {
        showToast("רשימת המשימות הועתקה ללוח בהצלחה!");
    }).catch(err => {
        alert("שגיאה בהעתקה: " + err);
    });
}

function downloadMarkdown() {
    if (!currentAudit) return;
    let md = `# דוח בדיקת מוכנות אתר למסירה - APEX // LaunchReady\n\n`;
    md += `**כתובת האתר:** \`${currentAudit.target_url}\`  \n`;
    md += `**תאריך בדיקה:** ${currentAudit.scan_time}  \n`;
    md += `**ציון מוכנות משוקלל:** ${currentAudit.overall_score}/100  \n`;
    md += `**ציון נגישות (ת"י 5568 / WCAG AA):** ${currentAudit.a11y_score}/100  \n`;
    md += `**ציון טכני ו-SEO:** ${currentAudit.tech_score}/100  \n\n`;

    md += `## סיכום מנהלים\n`;
    md += `> **${currentAudit.verdict.title}**  \n`;
    md += `> ${currentAudit.verdict.description}\n\n`;

    md += `## ✅ סעיפי נגישות שנבדקו ונמצאו תקינים (ת"י 5568 / WCAG 2.1 AA)\n\n`;
    const compData = currentAudit.a11y_compliance || currentAudit.raw_results?.a11y || {};
    const passed = compData.passed_checks || (compData.compliance_checks || []).filter(c => c.status === 'passed');
    if (passed.length) {
        passed.forEach(c => {
            md += `- [x] **${c.name}** (\`${c.standard}\`)\n`;
            md += `  - *פירוט:* ${c.details}\n\n`;
        });
    } else {
        md += `*לא נרשמו סעיפים תקינים.*\n\n`;
    }

    md += `## ♿ משימות נגישות לתיקון (תקן ת"י 5568 / WCAG AA)\n\n`;
    if (currentAudit.a11y_todos && currentAudit.a11y_todos.length) {
        currentAudit.a11y_todos.forEach(t => {
            const box = t.completed ? '[x]' : '[ ]';
            md += `- ${box} **${t.title}** (${t.priority})\n`;
            md += `  - **תקן רשמי:** \`${t.wcag_standard || 'ת"י 5568'}\`\n`;
            if (t.element) md += `  - קוד: \`${t.element}\`\n`;
            md += `  - **המלצה לתיקון:** ${t.recommendation}\n\n`;
        });
    } else {
        md += `*לא נמצאו ליקויי נגישות בדף.*\n\n`;
    }

    md += `## 🛠️ משימות טכניות, קישורים ו-SEO\n\n`;
    if (currentAudit.tech_todos && currentAudit.tech_todos.length) {
        currentAudit.tech_todos.forEach(t => {
            const box = t.completed ? '[x]' : '[ ]';
            md += `- ${box} **${t.title}** (${t.category_label} | ${t.priority})\n`;
            if (t.element) md += `  - קוד: \`${t.element}\`\n`;
            md += `  - **המלצה לתיקון:** ${t.recommendation}\n\n`;
        });
    } else {
        md += `*לא נמצאו תקלות טכניות בדף.*\n\n`;
    }

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `LaunchReady_Audit_${currentAudit.domain || 'report'}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
