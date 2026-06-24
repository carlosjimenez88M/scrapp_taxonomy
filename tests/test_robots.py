from unittest import TestCase

from scrapp_taxonomy.domain.models import HttpResource, RobotsAvailability
from scrapp_taxonomy.services.robots import StandardRobotsPolicyReader


class StandardRobotsPolicyReaderTest(TestCase):
    def test_disallows_target_for_matching_user_agent(self):
        robots = HttpResource(
            url="https://example.com/robots.txt",
            status_code=200,
            body="\n".join(
                [
                    "User-agent: *",
                    "Disallow: /private",
                    "Allow: /private/public",
                    "Sitemap: https://example.com/sitemap.xml",
                ]
            ),
        )

        policy = StandardRobotsPolicyReader().read(
            "https://example.com/private/data", robots, "scrapp-taxonomy/0.1"
        )

        self.assertEqual(RobotsAvailability.FOUND, policy.availability)
        self.assertFalse(policy.target_allowed)
        self.assertEqual(("https://example.com/sitemap.xml",), policy.sitemaps)
        self.assertEqual(("/private",), policy.matching_groups[0].disallow)

    def test_missing_robots_allows_fetching_by_convention(self):
        robots = HttpResource(
            url="https://example.com/robots.txt",
            status_code=404,
            body="",
        )

        policy = StandardRobotsPolicyReader().read(
            "https://example.com/public", robots, "scrapp-taxonomy/0.1"
        )

        self.assertEqual(RobotsAvailability.NOT_FOUND, policy.availability)
        self.assertTrue(policy.target_allowed)
