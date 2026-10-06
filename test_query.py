import httpx

res = httpx.post('http://127.0.0.1:8080/api/audit', json={
    'html': '<!DOCTYPE html><html><head><title>Test</title></head><body><p>x</p></body></html>',
    'check_live': False
})
d = res.json()
print("Success:", d.get("success"))
print("Total todos in response:", len(d.get("todos", [])))
print("Has a11y_todos in d?:", "a11y_todos" in d)
if "a11y_todos" in d:
    print("a11y_todos count:", len(d["a11y_todos"]))
print("Has tech_todos in d?:", "tech_todos" in d)
if "tech_todos" in d:
    print("tech_todos count:", len(d["tech_todos"]))
print("All keys returned by server:", list(d.keys()))
