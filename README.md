# Sleepy Thumb

A one-handed baby sleep & diaper tracker for 3am. One static page, dark warm colors,
three huge buttons: **Asleep**, **Awake**, **Diaper**.

## How to use

- **Asleep**: tap when Baby falls asleep. The screen shows a running "asleep for Xh Ym" timer
  and the **Awake** button grows so it's easy to hit next.
- **Awake**: tap when Baby wakes. The session length is shown in the log.
- **Diaper**: logs a change right away as *wet*. For 5 seconds you can tap **Dirty** or **Both**
  (or **Wet**) to change it; if you do nothing it stays *wet*.
- **Today**: total sleep today (a nap that crosses midnight only counts the part after midnight),
  number of diapers today, and today's log, newest first, in local time.
- **Undo** (top right): removes the last entry you added, after a confirm.
- **Edit** on any log row: change type, diaper kind or time, or delete the entry.
- **Export JSON / CSV** for a backup or a spreadsheet; **Import JSON** restores a JSON backup
  (replaces current data, after a confirm).

Add it to your phone's home screen (Share → Add to Home Screen / browser menu → Install) to use
it like an app. Once it has been opened online it also works offline (small service worker).

## Privacy

All data stays in this browser on this phone (`localStorage`). There is no server, no account,
no analytics, no external fonts or CDNs; a Content-Security-Policy blocks outside requests.
Clearing the browser's site data deletes the log, so export now and then if you want a backup.

## Run locally

No build step. Serve the folder with any static server:

```sh
cd sleepy-thumb
python3 -m http.server 8000
# open http://localhost:8000/
```

Opening `index.html` directly as a file also works (without offline support). All paths are
relative, so it works from a subpath such as GitHub Pages (`https://user.github.io/sleepy-thumb/`).

## Tests

`tests/e2e.py` is a Playwright (Python) end-to-end test at a 390×844 phone viewport using a fake
clock (sleep across midnight, totals, diaper follow-up, undo, edit/delete, persistence across reload,
export/import, offline, reduced motion, no console errors, no external requests).

```sh
pip install playwright && python3 -m playwright install chromium
cd .. && python3 -m http.server 8765 --bind 127.0.0.1 &
python3 sleepy-thumb/tests/e2e.py
```

## Files

- `index.html`: the whole app (inline CSS + vanilla JS)
- `manifest.json`, `icon.svg`, `icon-192.png`, `icon-512.png`: home-screen install
- `sw.js`: offline cache (network-first)
- `screenshots/`: phone screenshots
