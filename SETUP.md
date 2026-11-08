# Setting up Pando

Pando is one HTML file plus a data file. There is no build step,
no backend, and nothing to install to *use* it. This guide covers
three things: putting the starter corpus online, using a different
corpus, and making a corpus of your own.

## 1. Put it online (GitHub Pages)

The repo ships with a starter corpus (AI education + hardware),
so the fastest path to a live page is:

1. Push the repo contents to GitHub (files at the repo root:
   `index.html`, `corpus.json`, plus the docs and `tools/`).
2. In the repo: **Settings → Pages → Build and deployment →
   Source: Deploy from a branch**, branch `main`, folder `/ (root)`,
   **Save**.
3. After a minute your page is at
   `https://<your-username>.github.io/<repo-name>/`.

The page finds the `corpus.json` sitting next to it and renders
that corpus. Any static host works the same way (Netlify, a home
server, an S3 bucket) — Pages is just the zero-effort default.

**Running it locally:** serve the folder over HTTP, don't just
double-click the file:

```
python3 -m http.server 8000
# then open http://localhost:8000
```

Browsers block a `file://` page from reading the sibling
`corpus.json`; over HTTP it loads normally. (Over `file://` the
page still runs, but falls back to a tiny built-in demo corpus.)

## 2. Point it at a different corpus ("Change topic")

A corpus is any GitHub repo with a `corpus.json` at its root.
Switching topics is a load, not a setting:

- Click **🔀 Change topic** (top bar) and enter `user/repo` —
  Pando fetches that repo's `corpus.json` (tries `main`, then
  `master`). A full URL to any `corpus.json` works too.
- **Reset** in the same dialog returns to the built-in corpus.
- Shareable form: `index.html?corpus=user/repo` or
  `index.html?src=https://…/corpus.json`.

Liked videos, watch-later, history and playlists are stored in
your browser only, **per corpus** — each topic keeps its own
lists. Nothing is sent anywhere; there is no account.

## 3. Make your own corpus

### The five-minute version

Create a repo whose `corpus.json` is a list of YouTube links:

```json
{"title": "My topic",
 "videos": ["https://www.youtube.com/watch?v=VMj-3S1tku0",
            "dQw4w9WgXcQ"]}
```

That's a valid corpus. You get thumbnails and playback
immediately; titles are filled in best-effort at load. Point
Pando at the repo (step 2) and it becomes your tube.

### The full version (channels, categories, dates)

`tools/build_corpus.py` generates the full form — channels,
categories, durations, view counts, upload dates — from a list
of channels.

1. Install yt-dlp: `pip install yt-dlp` (a venv is fine).
2. Write `channels.json`:

   ```json
   [{"name": "Andrej Karpathy", "handle": "@AndrejKarpathy",
     "category": "Deep Learning"},
    {"name": "MIT OpenCourseWare", "handle": "@mitocw",
     "category": "Courses", "filter": "ai"}]
   ```

   `filter: "ai"` is for giant generalist channels: only videos
   whose titles match AI/ML keywords are kept.
3. Run it:

   ```
   python3 tools/build_corpus.py channels.json \
       --out corpus.json --title "My topic" --dates
   ```

   Per channel it keeps the **30 most-watched** videos of 60
   seconds or longer. `--dates` additionally fetches each kept
   video's upload date (powers the **Newest first** sort); it's
   slow — one full extraction per video — and cached in
   `date_cache.json`, so re-runs only fetch dates for new videos.
4. Commit `corpus.json` to your repo root and point Pando at it.

**Verify your handles.** The generator checks that each handle
resolves to the channel it claims to be and skips mismatches —
because handles get squatted. In the starter corpus's build, four
famous-looking handles turned out to belong to namesakes or dead
entities (the real ServeTheHome is `@ServeTheHomeVideo`, not
`@ServeTheHome`). If a channel you expected is missing, check the
generator's SKIP lines first.

### Refreshing a corpus

Re-run the generator and commit the new `corpus.json`. View
counts and the top-30 selection move over time; the date cache
keeps refreshes cheap.

## Notes and limits

- Playback and thumbnails load from YouTube, so the page needs
  youtube.com reachable. Auto-advance (playlists, TV mode) uses
  the YouTube IFrame API; if that fails to load, videos still
  play in a plain embed but won't auto-advance.
- The corpus data is links and public metadata only. Videos
  remain their creators' property and stream from YouTube.
- License: Apache-2.0. See `CORPUS.md` for the full format spec.
