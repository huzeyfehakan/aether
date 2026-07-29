"""Technical outbound adapter for retrieving source HTML over HTTP(S)."""

from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class HtmlFetchError(ValueError):
    """Raised when a web source cannot provide usable HTML."""


class HttpHtmlFetcher:
    """Fetch one user-supplied HTTP(S) page without interpreting its content."""

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HtmlFetchError("URL must be an absolute HTTP(S) URL")

        request = Request(url, headers={"User-Agent": "Aether-MVP-Demo/0.1"})
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                content_type = response.headers.get_content_type()
                if content_type not in {"text/html", "application/xhtml+xml"}:
                    raise HtmlFetchError("URL did not return an HTML document")
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except HTTPError as error:
            raise HtmlFetchError(f"URL returned HTTP {error.code}") from error
        except URLError as error:
            raise HtmlFetchError("URL could not be fetched") from error
