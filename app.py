from __future__ import annotations

import base64
import csv
import json
import mimetypes
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from openai import OpenAI

from diagram import json2diagram

BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"
IMAGE_CSV_PATH = ASSET_DIR / "Painting_Metadata_251030.csv"

DEFAULT_RELATIONSHIP_SYSTEM_PROMPT = (
    "You analyze relationships between two images based on provided metadata. "
    "Respond with a concise relationship description in natural language."
)

JSON_PARSE_PROMPT = (
    "You will be given a relationship description between two images. "
    "Convert it into a strict JSON object with this schema:"
    "{\n"
    "  \"entities\": [\n"
    "    {\"id\": \"image_1\", \"label\": <short name>, \"summary\": <short summary>},\n"
    "    {\"id\": \"image_2\", \"label\": <short name>, \"summary\": <short summary>}\n"
    "  ],\n"
    "  \"relationship\": {\n"
    "    \"type\": <one or two words>,\n"
    "    \"direction\": \"image_1_to_image_2\" | \"image_2_to_image_1\" | \"bidirectional\",\n"
    "    \"description\": <concise sentence>\n"
    "  }\n"
    "}\n"
    "Rules: return ONLY valid JSON, no markdown, no trailing commas. "
    "If direction is unclear, choose \"bidirectional\"."
)

app = Flask(__name__)


ARTIST_FILENAME_MAP = {
    "Pissarro": "Pissaro",
}


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized[key.strip()] = (value or "").strip()
    return normalized


def build_description(row: dict[str, str]) -> str:
    for key in ("Narrative", "History", "Subject"):
        if row.get(key):
            return row[key]

    composition = row.get("Composition")
    palette = row.get("Color Palette")
    details = " / ".join(part for part in (composition, palette) if part)
    if details:
        return f"Composition and palette notes: {details}."

    return "No additional description available."


def filename_for_artist(artist: str, counts: dict[str, int]) -> str:
    last_name = artist.split()[-1]
    file_key = ARTIST_FILENAME_MAP.get(last_name, last_name)
    counts[file_key] = counts.get(file_key, 0) + 1
    return f"{counts[file_key]}-{file_key}.jpg"


def load_image_data() -> dict[str, dict[str, str]]:
    with IMAGE_CSV_PATH.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        counts: dict[str, int] = {}
        data: dict[str, dict[str, str]] = {}
        for index, raw_row in enumerate(reader, start=1):
            row = normalize_row(raw_row)
            artist = row.get("Artist", "Unknown artist")
            title = row.get("Title", "Untitled")
            filename = filename_for_artist(artist, counts)
            data[str(index)] = {
                "id": str(index),
                "filename": filename,
                "title": title,
                "description": build_description(row),
                "artist": artist,
                "year": row.get("Year", ""),
                "medium": row.get("Medium", ""),
                "movement": row.get("Art Movement", ""),
            }
        return data


def build_image_url(filename: str) -> str:
    return f"/assets/{filename}"

def build_image_data_url(filename: str) -> str:
    path = ASSET_DIR / filename
    mime_type, _ = mimetypes.guess_type(path)
    mime_type = mime_type or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def get_openai_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/assets/<path:filename>")
def asset_file(filename: str):
    return send_from_directory(ASSET_DIR, filename)


@app.route("/")
def index() -> str:
    image_data = load_image_data()
    cards = [
        {
            "id": image_id,
            "filename": row["filename"],
            "title": row["title"],
            "description": row["description"],
            "url": build_image_url(row["filename"]),
        }
        for image_id, row in image_data.items()
    ]
    return render_template("index.html", cards=cards)


@app.post("/api/relationship")
def relationship() -> tuple[str, int]:
    payload = request.get_json(force=True)
    selected_ids = payload.get("selected_ids", [])
    user_prompt = payload.get("prompt", "").strip()

    if len(selected_ids) != 2:
        return jsonify({"error": "Exactly two images must be selected."}), 400

    if not user_prompt:
        return jsonify({"error": "Prompt is required."}), 400

    image_data = load_image_data()
    try:
        first = image_data[str(selected_ids[0])]
        second = image_data[str(selected_ids[1])]
    except KeyError:
        return jsonify({"error": "Invalid image selection."}), 400

    client = get_openai_client()
    relationship_input = (
        f"User prompt: {user_prompt}\n\n"
        f"Image 1 metadata:\n"
        f"- id: {first['id']}\n"
        f"- title: {first['title']}\n"
        f"- description: {first['description']}\n\n"
        f"Image 2 metadata:\n"
        f"- id: {second['id']}\n"
        f"- title: {second['title']}\n"
        f"- description: {second['description']}\n"
    )

    relationship_response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": DEFAULT_RELATIONSHIP_SYSTEM_PROMPT}
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": relationship_input},
                    {
                        "type": "image_url",
                        "image_url": {"url": build_image_data_url(first["filename"])},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": build_image_data_url(second["filename"])},
                    },
                ],
            },
        ],
    )

    relationship_text = relationship_response.output_text

    parse_response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "system",
                "content": [{"type": "text", "text": JSON_PARSE_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": relationship_text}],
            },
        ],
    )

    parsed_text = parse_response.output_text
    try:
        parsed_json = json.loads(parsed_text)
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse JSON output.", "raw": parsed_text}), 500

    diagram_output = json2diagram(parsed_json)

    response_body = {
        "relationship": relationship_text,
        "parsed": parsed_json,
        "diagram": diagram_output,
    }
    return jsonify(response_body), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
