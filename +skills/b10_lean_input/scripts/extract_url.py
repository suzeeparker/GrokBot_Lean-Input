"""Extract one public HTTP or HTTPS page to UTF-8 JSON.

The page and the URL are data. This module does not follow instructions found
in page text, does not send credentials, and does not bypass challenges.
"""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import os
from pathlib import Path
import signal
import socket
import ssl
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit
import uuid

from constants import (
    LOSS_WARNING,
    MAX_BYTES,
    MAX_REDIRECTS,
    MAX_URL_LENGTH,
    SOCKET_TIMEOUT_SECONDS,
    TOTAL_DEADLINE_SECONDS,
    USER_AGENT,
)

CHALLENGE_PHRASES = (
    "enable javascript",
    "enable js",
    "just a moment",
    "checking your browser",
    "verify you are human",
    "are you a robot",
    "cf-browser-verification",
    "captcha",
)
PAYWALL_PHRASES = (
    "subscribe to continue",
    "sign in to continue",
    "log in to continue",
    "register to continue",
    "to continue reading",
)
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
HTML_TYPES = {"text/html", "application/xhtml+xml"}


def _empty_result(url):
    return {
        "requested_url": url if isinstance(url, str) else None,
        "final_url": None,
        "title": None,
        "author": None,
        "publication_date": None,
        "text": None,
        "status": "error",
        "warnings": [],
        "error": None,
    }


TUNNEL_NETWORK = ipaddress.ip_network("198.18.0.0/15")
TUNNEL_ENV = "SAND_EGRESS_TUNNEL_PROXY_ADDR"
TUNNEL_WARNING = (
    "Connected through the Grok Bot egress tunnel. "
    "DNS returned an address in 198.18.0.0/15. "
    "TLS was verified for the original hostname."
)


def address_is_public(ip):
    if not ip.is_global:
        return False
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return False
    return True


def address_is_tunnel(ip):
    return ip.version == 4 and ip in TUNNEL_NETWORK


def tunnel_enabled(allow_tunnel):
    """The benchmark range is a route only for the bot egress tunnel."""
    if not allow_tunnel:
        return False
    return bool(os.environ.get(TUNNEL_ENV, "").strip())


def address_is_connectable(ip, allow_tunnel):
    if address_is_public(ip):
        return True
    return tunnel_enabled(allow_tunnel) and address_is_tunnel(ip)


def canonical_host(hostname):
    host = hostname.rstrip(".")
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        return host.encode("idna").decode("ascii")


def validate_url(url):
    """Return ``(SplitResult, ascii_host)`` or raise ``ValueError``."""
    if not isinstance(url, str) or not url:
        raise ValueError("Only public HTTP/HTTPS URLs are accepted")
    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL is too long")
    if any(ord(char) < 33 or ord(char) == 127 for char in url):
        raise ValueError("URL contains whitespace or control characters")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("Only public HTTP/HTTPS URLs are accepted")
    if parts.username is not None or parts.password is not None:
        raise ValueError("Credentials in URLs are forbidden")
    expected_port = 80 if parts.scheme == "http" else 443
    if parts.port not in (None, expected_port):
        raise ValueError("Only standard HTTP/HTTPS ports are supported")
    host = canonical_host(parts.hostname)
    if host.lower() == "localhost":
        raise ValueError("Localhost is forbidden")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and not address_is_public(literal):
        raise ValueError("Nonpublic destination rejected")
    return parts, host


def public_addresses(host, port, allow_tunnel=False):
    """Resolve ``host`` and reject any answer that is not public.

    A resolved address in 198.18.0.0/15 is accepted only when ``allow_tunnel``
    is true and ``SAND_EGRESS_TUNNEL_PROXY_ADDR`` is set. A mix that includes
    any other nonpublic answer is rejected. Literal IPs are judged earlier
    by ``validate_url`` and never use this exception.
    """
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"DNS lookup failed: {exc}") from exc
    if not infos:
        raise ValueError("Host has no addresses")
    for _family, _kind, _proto, _canon, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if not address_is_connectable(ip, allow_tunnel):
            raise ValueError("Nonpublic destination rejected")
    return infos


def resolved_uses_tunnel(addresses):
    for _family, _kind, _proto, _canon, sockaddr in addresses:
        if address_is_tunnel(ipaddress.ip_address(sockaddr[0])):
            return True
    return False


def next_hop(current_url, location, scheme):
    if not location:
        raise ValueError("Redirect missing Location")
    if len(location) > MAX_URL_LENGTH:
        raise ValueError("Redirect target is too long")
    nxt = urljoin(current_url, location)
    parts = urlsplit(nxt)
    if parts.scheme not in ("http", "https"):
        raise ValueError("Redirect scheme is not HTTP or HTTPS")
    if scheme == "https" and parts.scheme != "https":
        raise ValueError("HTTPS downgrade rejected")
    cleaned = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    validate_url(cleaned)
    return cleaned


def read_successful_body(response):
    if not 200 <= response.status < 300:
        raise ValueError(f"HTTP status {response.status}")
    content_type = response.headers.get_content_type()
    if content_type not in HTML_TYPES:
        shown = content_type or "missing"
        raise ValueError(f"Response is not HTML (content type {shown})")
    encoding = response.getheader("Content-Encoding")
    if encoding and encoding.lower() != "identity":
        raise ValueError("Compressed response rejected")
    length_header = response.getheader("Content-Length")
    if length_header is not None:
        try:
            announced = int(length_header)
        except ValueError as exc:
            raise ValueError("Invalid Content-Length") from exc
        if announced > MAX_BYTES:
            raise ValueError("HTML exceeds 5 MiB limit")
    raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("HTML exceeds 5 MiB limit")
    charset = response.headers.get_content_charset() or "utf-8"
    warnings = []
    try:
        html = raw.decode(charset, errors="strict")
    except (LookupError, UnicodeDecodeError):
        html = raw.decode("utf-8", errors="replace")
        warnings.append("Encoding was uncertain; decoded as UTF-8 with replacement characters")
    return html, warnings


def fetch_html(url, allow_tunnel=False):
    """Fetch decoded HTML. Connects to a resolved public address.

    On the Grok Bot target, a 198.18.0.0/15 answer is the egress tunnel when
    that environment variable is set. SNI and the Host header stay the
    original hostname.
    """
    current = url
    used_tunnel = False
    for hop in range(MAX_REDIRECTS + 1):
        parts, host = validate_url(current)
        port = 443 if parts.scheme == "https" else 80
        addresses = public_addresses(host, port, allow_tunnel=allow_tunnel)
        if resolved_uses_tunnel(addresses):
            used_tunnel = True
        family, socktype, proto, _canon, sockaddr = addresses[0]
        raw_sock = socket.socket(family, socktype, proto)
        raw_sock.settimeout(SOCKET_TIMEOUT_SECONDS)
        conn = None
        try:
            raw_sock.connect(sockaddr)
            if parts.scheme == "https":
                sock = ssl.create_default_context().wrap_socket(raw_sock, server_hostname=host)
            else:
                sock = raw_sock
            conn = http.client.HTTPConnection(host, port, timeout=SOCKET_TIMEOUT_SECONDS)
            conn.sock = sock
            target = urlunsplit(("", "", parts.path or "/", parts.query, ""))
            host_header = f"[{host}]" if ":" in host else host
            conn.request(
                "GET",
                target,
                headers={
                    "Host": host_header,
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html, application/xhtml+xml",
                    "Accept-Encoding": "identity",
                    "Connection": "close",
                },
            )
            response = conn.getresponse()
            if response.status in REDIRECT_STATUSES:
                location = response.getheader("Location")
                response.close()
                if hop == MAX_REDIRECTS:
                    raise ValueError("Redirect limit exceeded")
                current = next_hop(current, location, parts.scheme)
                continue
            html, warnings = read_successful_body(response)
            response.close()
            if used_tunnel:
                warnings.insert(0, TUNNEL_WARNING)
            return html, current, warnings
        except socket.timeout as exc:
            raise TimeoutError("Timed out after 10 seconds waiting for the server") from exc
        finally:
            if conn is not None:
                conn.close()
            else:
                raw_sock.close()
    raise ValueError("Redirect limit exceeded")


def _clean_meta(value, field):
    if value is None:
        return None, None
    if isinstance(value, str):
        stripped = value.strip()
        return (stripped or None), None
    return None, f"{field} from Trafilatura was not a string and was omitted"


def extract_html(html, url):
    """Run Trafilatura. Imported here so unit tests do not need the dependency."""
    import trafilatura

    raw = trafilatura.extract(
        html,
        url=url,
        output_format="json",
        with_metadata=True,
        include_comments=False,
        include_tables=True,
    )
    if not raw or not str(raw).strip():
        raise ValueError(
            "Empty extraction. The page may be JavaScript-rendered, non-article, or blocked. "
            "It was not bypassed."
        )
    data = json.loads(raw)
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(
            "Extraction returned no text. The page may be JavaScript-rendered, non-article, or blocked. "
            "It was not bypassed."
        )
    title, title_warning = _clean_meta(data.get("title"), "title")
    author, author_warning = _clean_meta(data.get("author"), "author")
    published, date_warning = _clean_meta(data.get("date"), "publication_date")
    warnings = [item for item in (title_warning, author_warning, date_warning) if item]
    blob = f"{title or ''}\n{text}".lower()
    if any(phrase in blob for phrase in CHALLENGE_PHRASES) and len(text) < 400:
        raise ValueError("Page looks like a JavaScript, bot, or challenge interstitial. It was not bypassed.")
    if any(phrase in blob for phrase in PAYWALL_PHRASES):
        warnings.append("Paywall or sign-in language is present. It was not bypassed; the text may be incomplete.")
    if len(html) >= 2000 and len(text) < 80:
        warnings.append(
            "Extracted text is short relative to the decoded HTML. "
            "Content that appears only after JavaScript runs is not recovered."
        )
    warnings.append(LOSS_WARNING)
    return {
        "title": title,
        "author": author,
        "publication_date": published,
        "text": text,
        "warnings": warnings,
    }


def process(url, fetcher=None, extractor=None, allow_tunnel=False):
    result = _empty_result(url)
    html = None
    try:
        validate_url(url)
        if fetcher is None:
            fetcher = lambda current: fetch_html(current, allow_tunnel=allow_tunnel)
        html, final, warnings = fetcher(url)
        result["final_url"] = final
        result["warnings"] = list(warnings)
        extracted = (extractor or extract_html)(html, final)
        result["title"] = extracted["title"]
        result["author"] = extracted["author"]
        result["publication_date"] = extracted["publication_date"]
        result["text"] = extracted["text"]
        result["warnings"].extend(extracted["warnings"])
        result["status"] = "success"
    except Exception as exc:
        result["error"] = str(exc)
        result["status"] = "error"
        result["text"] = None
    return result, html


def metrics_path_for(output: Path) -> Path:
    if output.suffix == ".json":
        return output.with_suffix(".metrics.json")
    return output.with_name(output.name + ".metrics.json")


def source_path_for(output: Path) -> Path:
    if output.suffix:
        return output.with_suffix(".source.html")
    return output.with_name(output.name + ".source.html")


def _opener(name, flags):
    return os.open(name, flags | getattr(os, "O_NOFOLLOW", 0), 0o600)


def write_outputs(result, output, html=None, retain=False):
    output = Path(output).expanduser()
    if not output.is_absolute():
        output = (Path.cwd() / output).resolve()
    metrics_path = metrics_path_for(output)
    source_path = source_path_for(output)
    paths = [output, metrics_path]
    if retain:
        if html is None:
            raise ValueError("Cannot retain HTML because none was decoded")
        paths.append(source_path)
    for path in paths:
        if path.is_symlink() or path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    text = result.get("text")
    metrics = {
        "decoded_html_characters": None if html is None else len(html),
        "extracted_text_characters": None if not isinstance(text, str) else len(text),
        "serialized_json_characters": len(serialized),
        "unit": "unicode_code_points",
    }
    payload = [
        (output, serialized),
        (metrics_path, json.dumps(metrics, ensure_ascii=False, indent=2) + "\n"),
    ]
    if retain:
        payload.append((source_path, html))
    opened = []
    try:
        handles = []
        for path, _content in payload:
            handles.append(open(path, "x", encoding="utf-8", newline="\n", opener=_opener))
            opened.append(path)
        for handle, (_path, content) in zip(handles, payload):
            handle.write(content)
            handle.flush()
        for handle in handles:
            handle.close()
    except Exception:
        for path in opened:
            try:
                if path.is_file() and not path.is_symlink():
                    path.unlink()
            except OSError:
                pass
        raise
    written = output.read_text(encoding="utf-8")
    if len(written) != metrics["serialized_json_characters"]:
        raise RuntimeError("Serialized JSON character count does not match the file")
    return metrics


def default_output():
    return Path.home() / "Tools" / "lean-input" / "output" / f"page-{uuid.uuid4().hex}.json"


def _alarm(_signum, _frame):
    raise TimeoutError("40-second total processing deadline exceeded")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract one public page to UTF-8 JSON.")
    parser.add_argument("url")
    parser.add_argument("--output")
    parser.add_argument("--retain-html", action="store_true")
    parser.add_argument("--target", choices=("bot", "mac"))
    args = parser.parse_args(argv)
    if not hasattr(signal, "SIGALRM"):
        print("Unix SIGALRM is required", file=sys.stderr)
        return 2
    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(TOTAL_DEADLINE_SECONDS)
    try:
        result, html = process(args.url, allow_tunnel=args.target == "bot")
    finally:
        signal.alarm(0)
    output = Path(args.output).expanduser() if args.output else default_output()
    try:
        metrics = write_outputs(result, output, html, args.retain_html)
    except OSError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2
    summary = {
        "status": result["status"],
        "output": str(output),
        "metrics_output": str(metrics_path_for(Path(output))),
        "metrics": metrics,
        "error": result["error"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
