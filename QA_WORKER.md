# QA_WORKER -- news-image-20261117 (entry `ni1117`)

Worker: `urgent-news17` (deadline 2026-11-19T00:00Z). Working dir `C:/script/x/entries/ni1117`.
Kit read: `C:/script/x/kits/news-image-20261117/news-image-20261117-kit/RULES.txt` plus the live
requirements at `GET https://make.fun/api/competitions/news-image-20261117/requirements`.

Status: **implementation complete and tested locally**. Not submitted, not pushed, no remote
created, no account touched. One thing is *not* established and is called out below: aesthetic
quality was never seen by an eye (this session has no image-vision capability), so the visual
verdict rests on programmatic checks plus a coarse text preview, not on a look at the picture.

---

## 1. What was actually built

| path | what it is |
|---|---|
| `main.ts` | graded runtime, Node stdlib only, copies `entry.png` to `$MAKEFUN_OUTPUT_DIR` or `/output` and re-reads it to re-check the gate limits |
| `entry.png` | the delivered picture, 1024x1024, 299933 bytes, sha256 `4240c4b3ca2484975bb55c24d8e9225883218a31c7a8883df8fcc2c6f044d5e8` |
| `render/render_entry.py` | build-time renderer (Pillow, Windows fonts). Data-driven, deterministic, validates the layout before writing |
| `render/news_verified.json` | the six verified stories with the URL, real headline, publication time and the sentence each claim is drawn from |
| `render/check_png.py` | stdlib gate validator: signature, size cap, dims, per-chunk CRC, IHDR..IEND wholeness, IDAT inflate + filter types, multi-file sha256 equality |
| `README.md` | minimal, current `how_to_submit.readme_template` badge block, no placeholders |

`LICENSE` (MIT) and `.makefun/owner.json` were left exactly as they were.

The pre-existing `entry.png` was an unverified draft; it was kept as the reference while the new
layout was designed and is preserved at sha256 `47aae3d5048759082cdb245c817e537af9e24be125664f738255f2207ee7d3bb`
(256377 bytes, 1024x1024) in the scratch dir, which is deleted at the end. `entry.png` itself is the
new render.

## 2. Independent verification of the news (real fetches, not HTTP 200)

Every story was fetched on 2026-11-18 with `curl -sS -m 30 -A "Mozilla/5.0"`, and the response's
`<title>`, `og:description` and `article:published_time`/`datePublished` were parsed and compared
with what the image says. The weekday was checked independently:
`python -c "import datetime; print(datetime.date(2026,11,17).strftime('%A'))"` -> `Tuesday`.

| card | drawn claim | fetched article | published | verdict |
|---|---|---|---|---|
| 1 | "Ukraine strikes Kerch Bridge with drones and missiles" | NPR: "Ukraine strikes major Russian bridge with drones and missiles as aerial attacks escalate" | 2026-11-17T04:50:45-05:00 | corroborated; body names the Kerch Bridge and attributes it to Zelenskyy |
| 2 | "Iran rejects 'no war, no peace'; US says no deal needed" | Al Jazeera: "Is the US-Israel war on Iran turning into a 'frozen conflict'?" | 2026-11-17T12:33:51Z | corroborated; description carries both halves verbatim |
| 3 | "Peltola beats Sullivan; Democrats reach 56 Senate seats" | Guardian: "Mary Peltola beats Republican Dan Sullivan in Alaska to give Democrats 56 Senate seats" | 2026-11-18T03:25:14Z | corroborated; 03:25Z 18 Nov is the evening of 17 Nov in US zones, so first reported on the 17th in *some* time zone as the RULES allow |
| 4 | "Fed's Lisa Cook refuses to attend White House hearing" | Al Jazeera: "US Fed's Lisa Cook refuses to attend White House hearing" | 2026-11-17T22:01:27Z | corroborated, image text is the article's own h1 |
| 5 | "NSA blames US network outage on routine maintenance" | Al Jazeera: "NSA attributes US network outage to routine 'maintenance' activities" | 2026-11-17T19:03:14Z | corroborated; "blames" is the article's own framing of the NSA's attribution |
| 6 | "Sen. Jack Reed says FAA needs a real plan, not just money" | NPR: h1 "Sen. Jack Reed says FAA needs a real plan, not just more money" | 2026-11-17T06:58:42-05:00 | corroborated, image text is the article's h1 |

Deliberately **not** asserted anywhere in the image: any casualty figure, any outcome of the Iran
war, any Senate total other than the 56 the Guardian states, any cause of the NSA outage beyond the
maintenance the NSA itself attributed, and any claim about the earlier nationwide ground stop beyond
Senator Reed's criticism of it. The Iran story is reported as a *question* ("frozen conflict?"), so
the image states only the two facts the description carries, not the framing.

Nothing was dropped for failing verification: all six researched stories corroborated. The draft's
framing was tightened, not the facts (`render/news_verified.json`, key `dropped`).

## 3. Real commands and their real output

Renderer (build time):

```
$ python render/render_entry.py render/news_verified.json entry.png
rendered entry.png
  size       : 1024x1024  bytes=299933  sha256=4240c4b3ca2484975bb55c24d8e9225883218a31c7a8883df8fcc2c6f044d5e8
  layout     : row_h=331 icon_h=135 strap_h=112 registered_text_boxes=37
  day named  : TUESDAY 17 NOVEMBER 2026
  widest text: 'Kerch Bridge struck · Iran talks at an impasse' box=(61.0, 181.7, 894.3, 209.7)
  widest text: 'WORLD NEWS' box=(35.7, 63.3, 539.3, 110.3)
  widest text: 'SOURCES · NPR · AL JAZEERA · THE GUARDIAN' box=(37.0, 984.0, 416.0, 994.0)
  checks     : canvas bounds OK, zone bounds OK, no text overlap, footer above y=1016, required date present
```

Runtime, twice into two separate output dirs:

```
$ MAKEFUN_OUTPUT_DIR=out1 node main.ts
entry.png written: 1024x1024, 299933 bytes
$ MAKEFUN_OUTPUT_DIR=out2 node main.ts
entry.png written: 1024x1024, 299933 bytes
$ sha256sum out1/entry.png out2/entry.png
4240c4b3ca2484975bb55c24d8e9225883218a31c7a8883df8fcc2c6f044d5e8 *out1/entry.png
4240c4b3ca2484975bb55c24d8e9225883218a31c7a8883df8fcc2c6f044d5e8 *out2/entry.png
```

Gate validator on both runtime outputs:

```
$ python render/check_png.py out1/entry.png out2/entry.png
signature   : ok (PNG, 299933 bytes <= 1048576)
structure   : ok (7 chunks, crc verified, IHDR..IEND clean)
header      : ok (IHDR 1024x1024, 8-bit, colour type 2)
pixels      : ok (3146752 bytes of scanlines, all filter types valid)
determinism : ok (2 runs produced the same sha256)
PASS: entry is within the gate
```

Renderer determinism, two more independent builds: both
`4240c4b3ca2484975bb55c24d8e9225883218a31c7a8883df8fcc2c6f044d5e8`, same as `entry.png`.

Badge liveness (the URLs now in `README.md`), each `HTTP 200`, `image/svg+xml`:
`/badge/news-image-20261117.svg` 5131 B, `.../meimekh/news-image-20261117/rank.svg` 1405 B,
`.../reward.svg` 1293 B.

README placeholder scan: `grep -n "{owner}\|{repo}\|{referral_code}\|img.shields" README.md` -> no
matches (every URL has the owner and repo filled in; no template placeholder survives).

## 4. The validation did real work (two genuine bugs it caught)

The first two builds were **rejected**, not written, and both rejections were real:

1. `LAYOUT: kicker and source pill collide on card 3`. Cause: `copy_fit` measured the kicker
   without its letter-spacing, so "N. AMERICA · CENTRAL BANK" fitted at 12px by the plain width
   but overflowed at 12px once 1.5u tracking was added and grew into the source pill.
   Fix: `line_w()` now adds `(len-1)*track` and the fitter uses it, with the kicker budget cut to
   `CARD_W - 100`.
2. `outside canvas: 'TUESDAY · 17 NOVEMBER 2026' (987.0, 984.0, 1231.0, 994.0)`. Cause: tracked
   text forced `anchor="la"`, so the right-aligned footer date was drawn from its right edge
   rightwards to x=1231. Fix: tracked drawing now honours the `r`/`m` anchor prefixes.

Both bugs were found by the bounds/overlap checks, which is what those checks exist for.

## 5. Visual check -- what it is and what it is not

`entry.png` was inspected programmatically, not by eye. Evidence gathered:

* a 78x39 luminance ASCII preview of the finished file shows the intended composition -- full-bleed
  gold rules top and bottom, a two-column masthead (title left, TUESDAY / 17 NOVEMBER 2026 right),
  the gold day strap, six cards in a 3x2 grid, and a footer line;
* all six icon panels contain real drawn content, not empty boxes: 719-1674 distinct colours per
  panel, luminance spanning near 0 to 255;
* text boxes are 37 and pairwise non-overlapping, all inside their declared zones, everything
  inside the canvas, footer above y=1016;
* at 300x300 the luminance histogram still splits across 8 bins, i.e. the contrast survives the
  downscale the judge's craft criterion talks about.

**What this does not establish:** whether the picture *looks* good. No vision model and no human
reviewed it in this session, so no claim is made that the composition, colour harmony or scene
legibility are polished. That judgement is unverified and is the honest blocker on the last
criterion.

## 6. Known limitations / not verified

* Aesthetic quality: unverified (see section 5). Nothing here should be read as "this will score".
* The judge's verdict is unknown by construction; no judge call was made and none can be.
* Regional spread is skewed to the US: of the six verified stories, one is European, one Middle
  Eastern and four are US (politics, central banking, networks, aviation). That is what the
  day's corroborated set contained; adding a wider beat would have meant drawing a story whose
  article page I could not fetch and check, which was not worth a fabricated claim.
* The `README.md` badge URLs use owner `meimekh` (the entrant's real GitHub owner, seen in the
  existing make.fun submission logs) and repo name `news-image-20261117` chosen here. If the parent
  creates the repository under a different name, those two `rank`/`reward` URLs must be renamed
  with it. The competition badge URL is name-independent and stays correct either way.
* The repo is a fresh git repo with a single local commit; nothing was pushed and no remote exists.
* Transcripts/run-record/bundle were **not** produced or checked: those are the parent's step.
