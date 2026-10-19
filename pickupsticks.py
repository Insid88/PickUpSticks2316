#!/usr/bin/env python3
"""Collect public TikTok creator and video data through the Research API."""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE = "https://open.tiktokapis.com/v2/research"
TIMEOUT_SECONDS = 30
CREATOR_FIELDS = (
    "username",
    "display_name",
    "bio_description",
    "avatar_url",
    "is_verified",
    "follower_count",
    "following_count",
    "likes_count",
    "video_count",
    "bio_url",
)
VIDEO_FIELDS = (
    "id",
    "username",
    "video_description",
    "create_time",
    "region_code",
    "view_count",
    "like_count",
    "comment_count",
    "share_count",
    "favorites_count",
    "hashtag_names",
    "video_duration",
)


class APIError(Exception):
    """An error returned by or encountered while calling TikTok's API."""


def normalize_username(value):
    username = value.strip().removeprefix("@")
    if not re.fullmatch(r"[A-Za-z0-9._]{1,24}", username):
        raise ValueError("username must be 1–24 letters, numbers, periods, or underscores")
    return username


def ensure_not_excluded(username, excluded_username):
    if username.casefold() == excluded_username.casefold():
        raise ValueError("refusing to collect the excluded account")


def validate_date_range(start_date, end_date):
    try:
        start = datetime.strptime(start_date, "%Y%m%d").date()
        end = datetime.strptime(end_date, "%Y%m%d").date()
    except ValueError as exc:
        raise ValueError("dates must be valid calendar dates in YYYYMMDD format") from exc
    if start > end:
        raise ValueError("start date must be on or before end date")
    if (end - start).days > 30:
        raise ValueError("TikTok Research API date ranges cannot exceed 30 days")


class TikTokResearchClient:
    def __init__(self, access_token):
        self.access_token = access_token

    def _post(self, endpoint, fields, body):
        url = f"{API_BASE}/{endpoint}/?{urlencode({'fields': ','.join(fields)})}"
        request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"******",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise APIError(f"TikTok API returned HTTP {exc.code}") from None
        except URLError as exc:
            raise APIError(f"Could not reach TikTok API: {exc.reason}") from None
        except (TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise APIError(f"Could not read a valid TikTok API response: {exc}") from None

        error = payload.get("error", {})
        if error.get("code") not in (None, "ok"):
            message = error.get("message") or "request failed"
            raise APIError(f"TikTok API error: {message}")
        return payload.get("data", {})

    def creator(self, username):
        data = self._post(
            "user/info",
            CREATOR_FIELDS,
            {"username": username},
        )
        if not isinstance(data, dict):
            raise APIError("TikTok API returned an unexpected creator response")
        return data

    def posts(self, username, start_date, end_date, max_count=100):
        validate_date_range(start_date, end_date)
        cursor = 0
        while True:
            data = self._post(
                "video/query",
                VIDEO_FIELDS,
                {
                    "query": {
                        "and": [
                            {
                                "operation": "EQ",
                                "field_name": "username",
                                "field_values": [username],
                            }
                        ]
                    },
                    "start_date": start_date,
                    "end_date": end_date,
                    "max_count": max_count,
                    "cursor": cursor,
                },
            )
            videos = data.get("videos", [])
            if not isinstance(videos, list):
                raise APIError("TikTok API returned an unexpected video response")
            yield from videos
            if not data.get("has_more"):
                break
            next_cursor = data.get("cursor")
            if next_cursor is None or next_cursor == cursor:
                raise APIError("TikTok API pagination did not advance")
            cursor = next_cursor


def write_jsonl(output_path, records):
    count = 0
    with Path(output_path).open("w", encoding="utf-8") as output:
        for record in records:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def build_parser():
    parser = argparse.ArgumentParser(
        description="Save public TikTok creator profiles or posts as JSONL."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    creator_parser = subparsers.add_parser("creator", help="look up a public creator profile")
    posts_parser = subparsers.add_parser("posts", help="collect a creator's public posts")

    for command_parser in (creator_parser, posts_parser):
        command_parser.add_argument("--username", required=True)
        command_parser.add_argument(
            "--exclude-username",
            required=True,
            help="your TikTok username, excluded from collection",
        )
        command_parser.add_argument("--output", required=True, help="output JSONL file")

    posts_parser.add_argument("--start-date", required=True, help="YYYYMMDD")
    posts_parser.add_argument("--end-date", required=True, help="YYYYMMDD")
    posts_parser.add_argument(
        "--max-count",
        type=int,
        default=100,
        choices=range(1, 101),
        help="videos per API page (1–100; default: 100)",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        username = normalize_username(args.username)
        excluded_username = normalize_username(args.exclude_username)
        ensure_not_excluded(username, excluded_username)
        if args.command == "posts":
            validate_date_range(args.start_date, args.end_date)
        access_token = os.environ.get("TIKTOK_RESEARCH_ACCESS_TOKEN")
        if not access_token:
            raise ValueError("set TIKTOK_RESEARCH_ACCESS_TOKEN to an approved Research API token")
        client = TikTokResearchClient(access_token)
        records = (
            [{"record_type": "creator", **client.creator(username)}]
            if args.command == "creator"
            else (
                {"record_type": "post", **video}
                for video in client.posts(
                    username,
                    args.start_date,
                    args.end_date,
                    args.max_count,
                )
            )
        )
        count = write_jsonl(args.output, records)
    except (APIError, OSError, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")
    print(f"Saved {count} record(s) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
