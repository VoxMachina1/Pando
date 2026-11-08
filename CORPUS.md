# The corpus format

A **corpus** is a GitHub repository containing a `corpus.json`
file at its root. The frontend renders any corpus you point it
at. Publishing a corpus is how you share a "-tube": your repo,
your taste, anyone's screen.

## Pointing the frontend at a corpus

- `index.html?corpus=USERNAME/REPO` — loads
  `corpus.json` from that GitHub repo (tries `main`, then
  `master`).
- `index.html?src=https://…/corpus.json` — loads from any URL.
- `index.html` with a `corpus.json` beside it — self-hosted
  mode, no parameters needed.
- The in-page **Corpus** button does the same thing from the UI.

## corpus.json — full form

```json
{
  "title": "AI Education",
  "subtitle": "The AI education canon, curated",
  "description": "How this corpus was chosen, in plain words.",
  "generated": "2026-11-07",
  "channels": [
    {"id": "karpathy", "name": "Andrej Karpathy",
     "handle": "@AndrejKarpathy", "category": "Deep Learning & Research"}
  ],
  "videos": [
    {"id": "VMj-3S1tku0", "title": "Let's build GPT: from scratch…",
     "channel": "karpathy", "duration": 6866, "views": 8900000,
     "published": "2023-02-08"}
  ]
}
```

- `id` is the YouTube video ID (the `v=` part).
- `duration` is seconds; `views` is a plain number. Both are
  optional — cards degrade gracefully.
- `published` is the upload date (`YYYY-MM-DD`), optional. It
  powers the **Newest first** sort; videos without it sort last
  under that view and show no date on the card.
- `channel` refers to a channel `id` in `channels`. Videos
  whose channel is missing render under "Unknown".
- Categories come from the channels; the UI builds its filter
  chips from whatever categories your corpus uses.

## corpus.json — minimal form ("a repo of YouTube links")

```json
{"title": "My links", "videos": ["https://www.youtube.com/watch?v=VMj-3S1tku0", "dQw4…"]}
```

A bare list of YouTube URLs or IDs is a valid corpus. You get
thumbnails and playback immediately; titles are filled in
best-effort at load. The full form is what you graduate to when
you want channels, categories, durations and view counts —
`tools/build_corpus.py` generates it from a channel list.

## Building a full corpus

`tools/build_corpus.py` takes a `channels.json` (name, handle,
category per channel), enumerates each channel's videos with
yt-dlp, keeps the top N by views, verifies that each handle
resolves to the channel it claims to be, and writes
`corpus.json`. With `--dates` it also fetches each kept video's
upload date (slow — one full extraction per video, cached in
`--date-cache` so rebuilds only fetch what's new). See the
script's header for usage.
