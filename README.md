⁶# PickUpSticks2316

PickUpSticks collects public TikTok creator profiles and public video-post
metadata through TikTok's Research API. It does not access private accounts,
direct messages, or reply text, and requires an explicit username to exclude
your own account.

## Access requirements

TikTok Research API access requires approval from TikTok and is limited to
eligible research projects. Apply through TikTok for Developers and follow
the API's terms and data-use requirements. This tool does not automate login,
scrape TikTok pages, or bypass API restrictions.

Set an approved access token in your environment; do not commit it:

```sh
export TIKTOK_RESEARCH_ACCESS_TOKEN="your-approved-token"
```

The tool uses only Python's standard library.

## Usage

Look up a public creator profile:

```sh
python3 pickupsticks.py creator \
  --username public_creator \
  --exclude-username your_handle \
  --output creator.jsonl
```

Collect a creator's public videos over a date range of at most 30 days:

```sh
python3 pickupsticks.py posts \
  --username public_creator \
  --exclude-username your_handle \
  --start-date 20260101 \
  --end-date 20260130 \
  --output posts.jsonl
```

The output is JSON Lines (one record per line); an existing output file is
overwritten. Video records include public post fields and aggregate counts
such as views, likes, comments, and shares, subject to TikTok's approved API
fields and availability. This does not collect individual reactors, comments,
or replies.

Run the test suite with:

```sh
python3 -m unittest discover -s tests
```
