import unittest
from unittest.mock import patch

from pickupsticks import (
    APIError,
    TikTokResearchClient,
    ensure_not_excluded,
    normalize_username,
    validate_record_username,
    validate_date_range,
)


class UsernameTests(unittest.TestCase):
    def test_normalizes_at_prefix_and_whitespace(self):
        self.assertEqual(normalize_username(" @creator.name "), "creator.name")

    def test_rejects_invalid_username(self):
        with self.assertRaises(ValueError):
            normalize_username("creator/name")

    def test_excluded_username_comparison_is_case_insensitive(self):
        with self.assertRaisesRegex(ValueError, "excluded account"):
            ensure_not_excluded("MyHandle", "myhandle")

    def test_rejects_video_returned_for_excluded_account(self):
        with self.assertRaisesRegex(ValueError, "excluded account"):
            validate_record_username({"username": "myhandle"}, "creator", "MyHandle")

    def test_rejects_records_without_creator_username(self):
        with self.assertRaisesRegex(APIError, "omitted the creator username"):
            validate_record_username({"id": "1"}, "creator", "myhandle")


class DateRangeTests(unittest.TestCase):
    def test_accepts_range_of_at_most_30_days(self):
        validate_date_range("20260101", "20260131")

    def test_rejects_ranges_longer_than_30_days(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed 30 days"):
            validate_date_range("20260101", "20260201")

    def test_rejects_reversed_dates(self):
        with self.assertRaisesRegex(ValueError, "on or before"):
            validate_date_range("20260102", "20260101")


class ClientTests(unittest.TestCase):
    @patch("pickupsticks.urlopen")
    def test_posts_follows_cursor_for_next_page(self, mock_urlopen):
        responses = [
            {"data": {"videos": [{"id": "first"}], "has_more": True, "cursor": 10}},
            {"data": {"videos": [{"id": "second"}], "has_more": False, "cursor": 10}},
        ]

        class Response:
            def __init__(self, payload):
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                import json

                return json.dumps(self.payload).encode()

        mock_urlopen.side_effect = [Response(payload) for payload in responses]
        client = TikTokResearchClient("test-token")

        videos = list(client.posts("creator", "20260101", "20260105"))

        self.assertEqual(videos, [{"id": "first"}, {"id": "second"}])
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("pickupsticks.urlopen")
    def test_raises_api_error_from_response(self, mock_urlopen):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b'{"error":{"code":"invalid_token","message":"token rejected"}}'

        mock_urlopen.return_value = Response()
        client = TikTokResearchClient("test-token")

        with self.assertRaisesRegex(APIError, "token rejected"):
            client.creator("creator")


if __name__ == "__main__":
    unittest.main()
