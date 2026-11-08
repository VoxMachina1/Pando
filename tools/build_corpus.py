#!/usr/bin/env python3
"""Build a corpus.json for the tube frontend from a channel list.

Usage:
  python3 build_corpus.py channels.json --out corpus.json \
      --title "AI Education" --subtitle "..." --description "..." \
      --top 30 --yt-dlp /path/to/yt-dlp

channels.json: [{"name": "...", "handle": "@x" OR "url": "https://...",
                 "category": "...", "filter": "ai" (optional)}]

How it works:
- Each channel is enumerated with yt-dlp's flat playlist mode
  (titles, durations, view counts — no downloads).
- IDENTITY CHECK: the channel name yt-dlp resolves must loosely
  match the expected name, or the channel is skipped and the
  mismatch printed. Handles get squatted; never trust them blind.
- Videos shorter than 60 seconds are dropped.
- Channels marked "filter": "ai" (giant generalists like MIT
  OpenCourseWare) keep only videos whose titles match the AI/ML
  keyword set below.
- Per channel, the top N by view count are kept.
- With --dates, each kept video also gets "published"
  (YYYY-MM-DD). Flat enumeration carries no dates, so this is a
  second pass: one full yt-dlp extraction per kept video,
  chunked across --date-workers parallel processes. It is slow
  (seconds per video); results are cached in --date-cache so
  rebuilds only fetch videos never dated before.
Requires: yt-dlp on PATH (or --yt-dlp). Python 3 stdlib only.
"""
import argparse, difflib, json, os, re, subprocess, sys, datetime, tempfile
from concurrent.futures import ThreadPoolExecutor

AI_KEYWORDS = re.compile(
    r"machine learning|deep learning|neural|artificial intelligence|\bAI\b|"
    r"data science|python|statistic|probabilit|linear algebra|calculus|"
    r"LLM|large language model|transformer|NLP|natural language|"
    r"computer vision|reinforcement|gradient|regression|classification|"
    r"clustering|bayes|tensor|PyTorch|TensorFlow|algorithm", re.I)

def enumerate_channel(ytdlp, url):
    r = subprocess.run([ytdlp, "--flat-playlist", "--dump-single-json", url],
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError((r.stderr or "no output")[-200:])
    return json.loads(r.stdout)

def fetch_dates(ytdlp, ids, cache_path, workers=8, chunk=25):
    """Return {video_id: 'YYYY-MM-DD'} using a JSON cache file."""
    cache = {}
    if cache_path and os.path.exists(cache_path):
        try:
            cache = json.load(open(cache_path))
        except Exception:
            cache = {}
    missing = [i for i in ids if i not in cache]
    print(f"dates: {len(ids) - len(missing)} cached, {len(missing)} to fetch",
          file=sys.stderr)

    def run_chunk(part):
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("\n".join("https://www.youtube.com/watch?v=" + i
                                  for i in part))
            r = subprocess.run([ytdlp, "-j", "--skip-download", "--no-warnings",
                                "--no-playlist", "--socket-timeout", "10",
                                "--retries", "2", "--batch-file", path],
                               capture_output=True, text=True, timeout=3600)
            found = {}
            for line in r.stdout.splitlines():
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                ud = d.get("upload_date")
                if d.get("id") and ud and len(ud) == 8:
                    found[d["id"]] = f"{ud[:4]}-{ud[4:6]}-{ud[6:]}"
            return found
        finally:
            os.unlink(path)

    if missing:
        parts = [missing[i:i + chunk] for i in range(0, len(missing), chunk)]
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for found in ex.map(run_chunk, parts):
                cache.update(found)
                if cache_path:
                    json.dump(cache, open(cache_path, "w"))
        print(f"dates: fetched {sum(1 for i in missing if i in cache)}"
              f"/{len(missing)}", file=sys.stderr)
    return cache


def name_matches(expected, resolved):
    if not resolved:
        return False
    e, r = expected.casefold(), resolved.casefold()
    return e in r or r in e or difflib.SequenceMatcher(None, e, r).ratio() > 0.45

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("channels")
    ap.add_argument("--out", default="corpus.json")
    ap.add_argument("--title", default="Untitled corpus")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--yt-dlp", default="yt-dlp")
    ap.add_argument("--dates", action="store_true",
                    help="also fetch upload dates for kept videos (slow)")
    ap.add_argument("--date-cache", default="date_cache.json")
    ap.add_argument("--date-workers", type=int, default=8)
    a = ap.parse_args()

    channels = json.load(open(a.channels))
    out = {"title": a.title, "subtitle": a.subtitle,
           "description": a.description,
           "generated": datetime.date.today().isoformat(),
           "channels": [], "videos": []}
    seen_ids = set()
    for i, ch in enumerate(channels):
        cid = re.sub(r"[^a-z0-9]+", "-", ch["name"].casefold()).strip("-") or f"ch{i}"
        url = ch.get("url") or f"https://www.youtube.com/{ch['handle']}"
        if ("/@" in url or "/channel/" in url) and not url.endswith("/videos"):
            url += "/videos"
        try:
            d = enumerate_channel(a.yt_dlp, url)
        except Exception as e:
            print(f"SKIP {ch['name']}: enumerate failed: {e}", file=sys.stderr)
            continue
        resolved = d.get("channel")
        if not name_matches(ch["name"], resolved):
            print(f"SKIP {ch['name']}: identity mismatch, resolved to {resolved!r}",
                  file=sys.stderr)
            continue
        vids = []
        for e in d.get("entries") or []:
            if not e.get("id") or e["id"] in seen_ids:
                continue
            dur = e.get("duration") or 0
            if dur and dur < 60:
                continue
            title = e.get("title") or ""
            if ch.get("filter") == "ai" and not AI_KEYWORDS.search(title):
                continue
            vids.append({"id": e["id"], "title": title, "channel": cid,
                         "duration": int(dur), "views": int(e.get("view_count") or 0)})
        vids.sort(key=lambda v: -v["views"])
        keep = vids[: a.top]
        for v in keep:
            seen_ids.add(v["id"])
        out["channels"].append({"id": cid, "name": ch["name"],
                                "handle": ch.get("handle", ""),
                                "category": ch.get("category", "")})
        out["videos"].extend(keep)
        print(f"OK {ch['name']}: {len(vids)} candidates -> kept {len(keep)}",
              file=sys.stderr)
    if a.dates:
        dates = fetch_dates(a.yt_dlp, [v["id"] for v in out["videos"]],
                            a.date_cache, a.date_workers)
        for v in out["videos"]:
            if v["id"] in dates:
                v["published"] = dates[v["id"]]
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"Wrote {a.out}: {len(out['channels'])} channels, {len(out['videos'])} videos")

if __name__ == "__main__":
    main()
