import unittest

from zed_pkg_insights.redaction import redact


class RedactionTests(unittest.TestCase):
    def test_redacts_bearer_and_github_tokens(self):
        source = "Authorization: Bearer secret123 ghp_123456789012345678901234567890123456"
        result = redact(source)
        self.assertNotIn("secret123", result)
        self.assertNotIn("ghp_", result)
        self.assertIn("redacted", result)

    def test_redacts_url_password(self):
        result = redact("https://alex:secret@example.test/path")
        self.assertEqual(result, "https://alex:<redacted>@example.test/path")


if __name__ == "__main__":
    unittest.main()
