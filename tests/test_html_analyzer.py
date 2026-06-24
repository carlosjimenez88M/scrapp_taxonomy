from unittest import TestCase

from scrapp_taxonomy.domain.models import FetchStatus, HttpResource
from scrapp_taxonomy.services.html_analyzer import StandardHtmlAnalyzer


class StandardHtmlAnalyzerTest(TestCase):
    def test_extracts_page_taxonomy(self):
        page = HttpResource(
            url="https://example.com/news",
            final_url="https://example.com/news",
            status_code=200,
            content_type="text/html",
            body="""
            <html lang="es">
              <head>
                <title>Noticias</title>
                <meta name="description" content="Resumen diario">
                <link rel="alternate" type="application/rss+xml" href="/feed.xml">
              </head>
              <body>
                <h1>Portada</h1>
                <a href="/2026/06/23/article-slug">Nota</a>
                <img src="/photo.jpg">
                <form action="/search" method="get"></form>
                <script type="application/ld+json">{"@type": "NewsArticle"}</script>
              </body>
            </html>
            """,
        )

        taxonomy = StandardHtmlAnalyzer().analyze(page)

        self.assertEqual(FetchStatus.FETCHED, taxonomy.status)
        self.assertEqual("Noticias", taxonomy.title)
        self.assertEqual("Resumen diario", taxonomy.meta_description)
        self.assertEqual("es", taxonomy.language)
        kinds = {candidate.kind for candidate in taxonomy.candidates}
        self.assertIn("article_links", kinds)
        self.assertIn("structured_data", kinds)
        self.assertIn("feeds", kinds)

    def test_keeps_document_title_when_svg_title_appears_later(self):
        page = HttpResource(
            url="https://example.com/news",
            final_url="https://example.com/news",
            status_code=200,
            body="""
            <html>
              <head><title>Document title</title></head>
              <body>
                <svg><title>Close icon</title></svg>
                <a href="https://social.example/account">External</a>
                <a href="/2026/06/23/article-slug">Article</a>
              </body>
            </html>
            """,
        )

        taxonomy = StandardHtmlAnalyzer().analyze(page)

        self.assertEqual("Document title", taxonomy.title)
        article_links = next(
            candidate for candidate in taxonomy.candidates if candidate.kind == "article_links"
        )
        self.assertEqual(("https://example.com/2026/06/23/article-slug",), article_links.sample)
