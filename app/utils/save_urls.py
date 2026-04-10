import os
import re
from typing import List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup
from bs4.element import Tag

from .prepare_vectordb import ensure_user_dirs, get_user_dirs

# Add a global variable to track first scan
first_scan_done = False

def save_url_to_vectordb_user(
        username: str,
        url: str,
        existing_docs: List[str],
        crawl_links: bool = False,
        page_limit: int = 50,
        _visited: Optional[Set[str]] = None,
        _crawl_count: Optional[list] = None
) -> Tuple[str, str]:
    """
    Fetch a URL and save it to user-specific docs folder
    """
    # Get user-specific docs directory
    dirs = ensure_user_dirs(username)
    docs_dir = dirs['docs']

    # Initialize for the first call in a crawl session
    if _visited is None:
        _visited = set()
    if _crawl_count is None:
        _crawl_count = [0, False]

    # Stop if page limit is reached during a crawl
    if crawl_links and _crawl_count[0] >= page_limit:
        if not _crawl_count[1]:
            st.info(f"Page limit ({page_limit}) reached for user {username}")
            _crawl_count[1] = True
        return "", ""

    if url in _visited:
        return "", ""

    _visited.add(url)

    if crawl_links:
        _crawl_count[0] += 1
        st.info(f"Processing page {_crawl_count[0]}/{page_limit} for {username}: {url}")

    # Fetch URL content (same as before)
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TNTBot/1.0)"},
            timeout=10
        )
        resp.raise_for_status()
    except Exception as e:
        st.error(f"❌ Failed to fetch {url} for {username}: {e}")
        return "", ""

    # Process content (same logic as before, but save to user's docs_dir)
    parsed = urlparse(url)
    base = slugify(parsed.netloc + parsed.path)
    ctype = resp.headers.get("Content-Type", "").lower()
    is_pdf = url.lower().endswith(".pdf") or "application/pdf" in ctype

    if is_pdf:
        fname = f"{base}.pdf"
        if fname in existing_docs:
            return "", "pdf"
        path = os.path.join(docs_dir, fname)
        with open(path, "wb") as f:
            f.write(resp.content)
        st.success(f"✅ Saved PDF for {username}: {url}")
        existing_docs.append(fname)
        return fname, "pdf"

    # HTML processing (same as before)
    encoding = resp.encoding if resp.encoding else 'utf-8'
    html_text = resp.content.decode(encoding, errors='replace')
    text = extract_all_visible_text(html_text)

    if not text:
        return "", "html"

    fname = f"{base}.html.txt"
    if fname in existing_docs:
        return "", "html"
    path = os.path.join(docs_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    st.success(f"✅ Saved HTML for {username}: {url}")
    existing_docs.append(fname)

    # Recursive crawling for same domain
    if crawl_links:
        links = extract_same_domain_links(html_text, url)
        for link in links:
            save_url_to_vectordb_user(
                username, link, existing_docs, crawl_links, page_limit, _visited, _crawl_count
            )

    return fname, "html"

def slugify(text: str) -> str:
    """Generate a filesystem-safe slug from the given text."""
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    return slug.strip('_')


def extract_all_visible_text(html: str) -> str:
    """
    Extracts all visible text from an HTML document,
    excluding scripts, styles, nav bars (after first scan), and other non-content elements.
    """
    global first_scan_done
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "noscript", "meta", "iframe"]):
        tag.decompose()

    # Remove nav bar after first scan
    if first_scan_done:
        # Remove by common nav bar tags/classes/ids
        nav_selectors = [
            'nav',
            '[class*="nav"]',
            '[class*="menu"]',
            '[class*="header"]',
            '[id*="nav"]',
            '[id*="menu"]',
            '[id*="header"]',
            '[role="navigation"]'
        ]
        for selector in nav_selectors:
            for nav in soup.select(selector):
                nav.decompose()
    # Mark first scan as done
    if not first_scan_done:
        first_scan_done = True

    # Extract text
    raw_text = soup.get_text(separator="\n")

    # Normalize whitespace
    lines = [line.strip() for line in raw_text.splitlines()]
    lines = [line for line in lines if line]

    return "\n\n".join(lines)


def extract_same_domain_links(html: str, base_url: str) -> List[str]:
    """
    Extract all same-domain links from HTML content, skipping English versions and image files.
    """
    soup = BeautifulSoup(html, "html.parser")
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    base_scheme = parsed_base.scheme
    links = set()
    for a in soup.find_all("a", href=True):
        if not isinstance(a, Tag):
            continue
        href = a.get('href', None)
        if not isinstance(href, str):
            continue
        href = href.strip()
        # Ignore mailto, javascript, etc.
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)
        # Accept relative links (netloc empty) or same-domain links
        if parsed.netloc and parsed.netloc != base_domain:
            continue
        if parsed.scheme not in ("http", "https", ""):
            continue
        # Skip English version links
        if '/en/' in parsed.path or parsed.path.endswith('/en'):
            continue
        # Skip image files
        if parsed.path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp')):
            continue
        links.add(abs_url)
    return list(links)

def save_url_to_vectordb(
    url: str,
    existing_docs: List[str],
    docs_dir: str = "docs",
    crawl_links: bool = False,
    page_limit: int = 50,
    _visited: Optional[Set[str]] = None,
    _crawl_count: Optional[list] = None
) -> Tuple[str, str]:
    """
    Fetch a URL (HTML or PDF), save it to `docs/`, and tell the caller
    what filename was written and of which type. Optionally crawl all same-domain links
    up to a page limit.

    Returns:
      (filename, file_type) where file_type is "pdf" or "html".
      If nothing was written (already exists or error), filename == "".
    """
    # Initialize for the first call in a crawl session
    if _visited is None:
        _visited = set()
    if _crawl_count is None:
        _crawl_count = [0, False] # [count, limit_reached_flag]

    # Stop if page limit is reached during a crawl
    if crawl_links and _crawl_count[0] >= page_limit:
        if not _crawl_count[1]: # If the limit message hasn't been printed yet
            print(f"Page limit ({page_limit}) reached. Halting further crawling.")
            _crawl_count[1] = True # Mark that the message has been printed
        return "", ""
        
    if url in _visited:
        print(f"Skipping already visited: {url}")
        return "", ""

    _visited.add(url)
    
    # This is a new page being processed, so increment the counter if crawling
    if crawl_links:
        _crawl_count[0] += 1
        print(f"Processing page {_crawl_count[0]}/{page_limit}: {url}")

    # 1) Fetch the URL content
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; TNTBot/1.0)"},
            timeout=10
        )
        resp.raise_for_status()
    except Exception as e:
        st.error(f"❌ Failed to fetch {url}: {e}")
        return "", ""

    os.makedirs(docs_dir, exist_ok=True)
    parsed = urlparse(url)
    base = slugify(parsed.netloc + parsed.path)
    ctype = resp.headers.get("Content-Type", "").lower()
    is_pdf = url.lower().endswith(".pdf") or "application/pdf" in ctype

    if is_pdf:
        fname = f"{base}.pdf"
        if fname in existing_docs:
            return "", "pdf"
        path = os.path.join(docs_dir, fname)
        with open(path, "wb") as f:
            f.write(resp.content)
        st.success(f"✅ Saved PDF: {url}")
        existing_docs.append(fname)
        return fname, "pdf"

    encoding = resp.encoding if resp.encoding else 'utf-8'
    html_text = resp.content.decode(encoding, errors='replace')
    text = extract_all_visible_text(html_text)

    if not text:
        return "", "html"

    fname = f"{base}.html.txt"
    if fname in existing_docs:
        return "", "html"
    path = os.path.join(docs_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    st.success(f"✅ Saved HTML: {url}")
    existing_docs.append(fname)

    if crawl_links:
        links = extract_same_domain_links(html_text, url)
        for link in links:
            # The check at the top of the function handles the limit for recursion
            save_url_to_vectordb(
                link, existing_docs, docs_dir, crawl_links, page_limit, _visited, _crawl_count
            )

    return fname, "html"
