#!/usr/bin/env python3
"""Daily cron: fetch YouTube stats for each uploaded video, score by niche, update learnings."""
import json, os, sys
from datetime import datetime, timedelta

sys.path.insert(0, "/opt/handholding-engine/apps/api")

# Load env
from dotenv import load_dotenv
load_dotenv("/opt/handholding-engine/apps/api/.env")

CLIENT_ID     = os.environ.get("YOUTUBE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
STATS_FILE    = "/opt/handholding-engine/data/video_stats.json"
LEARNINGS_FILE = "/opt/handholding-engine/data/learnings.json"

def get_yt():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import google.auth.transport.requests as gr
    creds = Credentials(
        token=None, refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(gr.Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def run():
    try:
        with open(STATS_FILE) as f:
            videos = json.load(f)
    except Exception:
        print("No stats file yet"); return

    now = datetime.utcnow()
    yt = get_yt()
    updated = False

    for v in videos:
        uploaded_at = datetime.fromisoformat(v["uploaded_at"])
        # Only check videos older than 72h
        if (now - uploaded_at).total_seconds() < 72 * 3600:
            continue
        # Don't re-check more than once per 24h
        last = v.get("last_checked")
        if last and (now - datetime.fromisoformat(last)).total_seconds() < 24 * 3600:
            continue

        try:
            resp = yt.videos().list(part="statistics", id=v["video_id"]).execute()
            if not resp.get("items"):
                continue
            s = resp["items"][0]["statistics"]
            views    = int(s.get("viewCount", 0))
            likes    = int(s.get("likeCount", 0))
            comments = int(s.get("commentCount", 0))
            v["views"]        = views
            v["likes"]        = likes
            v["comments"]     = comments
            v["score"]        = views + (likes * 10) + (comments * 5)
            v["last_checked"] = now.isoformat()
            updated = True
            print(f"  {v['video_id']} | {v['niche']} | views={views} likes={likes} score={v['score']}")
        except Exception as e:
            print(f"  Error {v['video_id']}: {e}")

    if updated:
        with open(STATS_FILE, "w") as f:
            json.dump(videos, f, indent=2)

    # Compute niche averages from all scored videos
    niche_scores: dict[str, list[int]] = {}
    for v in videos:
        if "score" in v:
            niche_scores.setdefault(v["niche"], []).append(v["score"])

    niche_ranked = sorted(
        [(n, round(sum(s) / len(s), 1)) for n, s in niche_scores.items()],
        key=lambda x: x[1], reverse=True
    )
    learnings = {"top_niches": niche_ranked, "updated_at": now.isoformat(), "total_videos": len(videos)}
    with open(LEARNINGS_FILE, "w") as f:
        json.dump(learnings, f, indent=2)

    print(f"\nTop niches: {niche_ranked[:5]}")
    print(f"Learnings written to {LEARNINGS_FILE}")

if __name__ == "__main__":
    run()
