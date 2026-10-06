import httpx

res = httpx.post('http://127.0.0.1:8080/api/audit', json={
    'url': 'https://www.histadrut.org.il/hotels/',
    'check_live': False,
    'scope_path': '/hotels',
    'exclude_header_footer': True
}, timeout=30.0)

d = res.json()
print("Verdict:", d.get("verdict"))
print("Total todos count:", len(d.get("todos", [])))
print("a11y_todos count:", len(d.get("a11y_todos", [])))
print("tech_todos count:", len(d.get("tech_todos", [])))
print("raw_results.links.broken_links_count:", d.get("raw_results", {}).get("links", {}).get("broken_links_count"))
print("raw_results.images.missing_alt_count:", d.get("raw_results", {}).get("images", {}).get("missing_alt_count"))
print("Todo titles:")
for t in d.get("todos", []):
    print(" - ", t["id"], t["category"], t.get("is_accessibility"), t["title"])
