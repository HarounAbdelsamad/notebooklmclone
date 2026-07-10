from app.models.enums import SourceType
from app.parsing.base import ParsedDocument, TextBlock, register
from app.utils.net import safe_get


def _extract_main_text(html: str, url: str | None) -> str:
    import trafilatura

    extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=True)
    if extracted:
        return extracted
    # Fallback: strip tags with BeautifulSoup.
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n")


@register(SourceType.html)
class HtmlParser:
    def parse(self, *, data: bytes | None, url: str | None, filename: str) -> ParsedDocument:
        if data is None:
            raise ValueError("HTML parser requires file bytes")
        html = data.decode("utf-8", errors="replace")
        text = _extract_main_text(html, url)
        return ParsedDocument(blocks=[TextBlock(text=text)], meta={"parser": "trafilatura"})


@register(SourceType.url)
class UrlParser:
    def parse(self, *, data: bytes | None, url: str | None, filename: str) -> ParsedDocument:
        if not url:
            raise ValueError("URL parser requires a source url")
        # safe_get applies the SSRF guard (scheme + resolved-IP checks) on every redirect hop.
        resp = safe_get(url, timeout=30.0)
        resp.raise_for_status()
        text = _extract_main_text(resp.text, url)
        title = None
        try:
            from bs4 import BeautifulSoup

            title_tag = BeautifulSoup(resp.text, "html.parser").title
            title = title_tag.string.strip() if title_tag and title_tag.string else None
        except Exception:
            title = None
        return ParsedDocument(
            blocks=[TextBlock(text=text)], meta={"parser": "trafilatura", "title": title}
        )
