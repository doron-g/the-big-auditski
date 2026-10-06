import asyncio
import httpx
from main import app

async def test_fastapi():
    # Use ASGITransport to test app directly without opening network socket
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Test index page
        res_index = await client.get("/")
        print("GET / status:", res_index.status_code)
        assert res_index.status_code == 200, "Index should return 200"

        # Test sample html endpoint
        res_sample = await client.get("/api/sample-html")
        print("GET /api/sample-html status:", res_sample.status_code)
        assert res_sample.status_code == 200
        sample_html = res_sample.json()["html"]

        # Test audit endpoint
        res_audit = await client.post("/api/audit", json={"html": sample_html, "check_live": False})
        print("POST /api/audit status:", res_audit.status_code)
        assert res_audit.status_code == 200
        data = res_audit.json()
        print("Audit success:", data["success"])
        print("Audit score:", data["overall_score"])
        print("Verdict title:", data["verdict"]["title"])
        print("TODO items count:", len(data["todos"]))
        print("TEST PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_fastapi())
