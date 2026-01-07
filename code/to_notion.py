import os
import requests
from google import genai
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID_KEY")
client = genai.Client(api_key=os.getenv("gemini_api_key"))

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def get_preview(title, author):
    prompt = f"Give a 4-5 sentence summary of '{title}' by {author}. No spoilers."
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite", 
        contents=prompt
    )
    return response.text

def fetch_book(book_name):
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": book_name, "maxResults": 3}
    response = requests.get(url, params=params).json()

    if "items" not in response:
        raise Exception("Book not found")
    
    for item in response["items"]:
        volume = item.get("volumeInfo", {})
        if "title" not in volume:
            continue

        images = volume.get("imageLinks", {})
        cover = (
            images.get("extraLarge")
            or images.get("large")
            or images.get("medium")
            or images.get("thumbnail")
            or ""
        )

        if cover:
            cover = cover.replace("zoom=1", "zoom=0")

        return {
            "title": volume.get("title", ""),
            "authors": ", ".join(volume.get("authors", [])),
            "pages": volume.get("pageCount", 0),
            "year": volume.get("publishedDate", "")[:4],
            "cover": cover
        }
    raise Exception("No valid book data found")
def add_to_notion(book, preview_text):
    url = "https://api.notion.com/v1/pages"

    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": book["title"]}}]
            },
            "Author": {
                "rich_text": [{"text": {"content": book["authors"]}}]
            },
            "Page": {
                "number": book["pages"]
            },
            "Status": {
                "select": {"name": "To Read"}
            }
        },
        "children": [
            {
                "object": "block",
                "type": "toggle",
                "toggle": {
                    "rich_text": [{ "type": "text", "text": {"content": f"🤖 AI Preview"}}],
                    "children" : [{"object": "block", "type": "paragraph", "paragraph": {
                                "rich_text": [{"text": {"content": preview_text}}]
                                }}],
                    "color": "gray_background"
                }
            }
        ]
    }
    if book["cover"]:
        data["cover"] = {
            "external": {
                "url": book["cover"]
            }
        }
    response = requests.post(url, headers=HEADERS, json=data)
    response.raise_for_status()

