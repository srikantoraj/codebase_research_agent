"""
Run sample questions through the API after the server is running.

Example:
python scripts/run_sample_questions.py
"""

import json
import urllib.request

payload = {
    "repo_url": "https://github.com/tiangolo/fastapi",
    "question": "How does FastAPI handle dependency injection internally?",
    "options": {"max_steps": 8, "reuse_previous_findings": True, "stream_events": True},
}

request = urllib.request.Request(
    "http://localhost:8000/api/research/sessions/",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(request) as response:
    print(response.read().decode("utf-8"))
