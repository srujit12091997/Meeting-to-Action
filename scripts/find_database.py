"""Ask Notion which databases our integration can see, and print their IDs.

Avoids hunting for the ID in the URL. Also doubles as a connection check:
if your database does NOT show up here, the integration isn't connected to it
yet (fix: open the database -> ... menu -> Connections -> add the integration).

Usage:
    python scripts/find_database.py
"""
from notion_client import Client

from app.config import get_settings


def _title_of(obj: dict) -> str:
    # Databases carry their title in obj["title"]; pages vary. Best-effort.
    title = obj.get("title") or []
    if title:
        return "".join(t.get("plain_text", "") for t in title)
    return "(untitled)"


def main() -> None:
    settings = get_settings()
    if not settings.notion_api_key:
        print("NOTION_API_KEY is empty in .env — add your token first.")
        return

    client = Client(auth=settings.notion_api_key, notion_version="2022-06-28")
    results = client.search(filter={"property": "object", "value": "database"}).get(
        "results", []
    )

    if not results:
        print("No databases visible to this integration.")
        print("--> Open your database in Notion, click the '...' menu, choose")
        print("    Connections / Add connections, and add 'Meeting-to-Action Agent'.")
        return

    print(f"Found {len(results)} database(s) the integration can access:\n")
    for db in results:
        db_id = db["id"].replace("-", "")
        print(f"  Title : {_title_of(db)}")
        print(f"  ID    : {db_id}")
        print(f"  (put this in .env as NOTION_DATABASE_ID={db_id})\n")


if __name__ == "__main__":
    main()
