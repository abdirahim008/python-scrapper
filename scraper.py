"""
SomaliJobs.com Scraper
=======================
Fetches job listings from somalijobs.com, then visits each job page
to extract full details from JSON-LD structured data and HTML sections.

Same approach as the Chrome extension but runs server-side.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

# ==========================================
# CONFIG
# ==========================================

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

REQUEST_DELAY = 1.5  # seconds between requests (respectful)
MAX_JOBS = 100       # max jobs per scrape run

# Location slug → proper name
LOCATION_NAMES = {
    'mogadishu': 'Mogadishu', 'muqdisho': 'Mogadishu', 'hargeisa': 'Hargeisa',
    'hargeysa': 'Hargeisa', 'kismayo': 'Kismayo', 'kismaayo': 'Kismayo',
    'baidoa': 'Baidoa', 'baydhabo': 'Baidoa', 'garowe': 'Garowe',
    'garoowe': 'Garowe', 'bosaso': 'Bosaso', 'boosaaso': 'Bosaso',
    'jowhar': 'Jowhar', 'jawhar': 'Jowhar', 'beledweyne': 'Beledweyne',
    'galkacayo': 'Galkayo', 'galkayo': 'Galkayo', 'berbera': 'Berbera',
    'burao': 'Burao', 'burco': 'Burao', 'beledhawa': 'Beledhawa',
    'sheekh': 'Sheekh', 'jigjiga': 'Jigjiga', 'nairobi': 'Nairobi',
    'djibouti': 'Djibouti', 'somaliland': 'Somaliland', 'puntland': 'Puntland',
    'somalia': 'Somalia', 'somalia-and-somaliland': 'Somalia & Somaliland',
    'puntland-state-of-somalia': 'Puntland, Somalia', 'mogadiscio': 'Mogadishu',
}

# Country detection
COUNTRY_MAP = {
    'mogadishu': 'Somalia', 'hargeisa': 'Somalia', 'kismayo': 'Somalia',
    'baidoa': 'Somalia', 'garowe': 'Somalia', 'bosaso': 'Somalia',
    'jowhar': 'Somalia', 'beledweyne': 'Somalia', 'galkayo': 'Somalia',
    'berbera': 'Somalia', 'burao': 'Somalia', 'somaliland': 'Somalia',
    'puntland': 'Somalia', 'somalia': 'Somalia',
    'nairobi': 'Kenya', 'mombasa': 'Kenya', 'kenya': 'Kenya',
    'kampala': 'Uganda', 'djibouti': 'Djibouti', 'jigjiga': 'Ethiopia',
    'addis ababa': 'Ethiopia',
}


def prettify_location(slug):
    if not slug:
        return ''
    key = slug.lower().strip()
    return LOCATION_NAMES.get(key, slug.replace('-', ' ').title())


def detect_country(location):
    if not location:
        return 'Somalia'
    loc_lower = location.lower()
    for kw, country in COUNTRY_MAP.items():
        if kw in loc_lower:
            return country
    return 'Somalia'


def clean_text(text):
    """Remove encoding artifacts"""
    if not text:
        return ''
    text = (text
        .replace('\u00a0', ' ')     # non-breaking space
        .replace('Â', '')            # double-encoding artifact
        .replace('·', '•')           # middle dot
    )
    # Replace any remaining [email protected] placeholders
    text = re.sub(r'\[email\s*protected\]', '[see original posting for email]', text, flags=re.I)
    # Clean excessive whitespace
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return '\n'.join(line.strip() for line in text.split('\n')).strip()


def decode_cf_email(encoded):
    """Decode Cloudflare obfuscated email.
    Cloudflare encodes emails as hex: first byte = XOR key, rest = XOR'd chars"""
    try:
        key = int(encoded[:2], 16)
        return ''.join(chr(int(encoded[i:i+2], 16) ^ key) for i in range(2, len(encoded), 2))
    except (ValueError, IndexError):
        return ''


def deobfuscate_emails(soup):
    """Find and decode all Cloudflare-obfuscated emails in a BeautifulSoup doc"""
    # Pattern 1: <a class="__cf_email__" data-cfemail="hex">
    for tag in soup.find_all(attrs={'data-cfemail': True}):
        decoded = decode_cf_email(tag['data-cfemail'])
        if decoded:
            # Replace the tag with the decoded email
            tag.replace_with(decoded)

    # Pattern 2: <a href="/cdn-cgi/l/email-protection#hex">
    for tag in soup.find_all('a', href=re.compile(r'/cdn-cgi/l/email-protection')):
        href = tag.get('href', '')
        match = re.search(r'#([0-9a-fA-F]+)', href)
        if match:
            decoded = decode_cf_email(match.group(1))
            if decoded:
                tag['href'] = f'mailto:{decoded}'
                if tag.string == '[email\xa0protected]' or tag.string == '[email protected]':
                    tag.string = decoded

    # Pattern 3: Encoded strings in text content
    # Sometimes the encoded string appears as template text
    return soup


def job_uid(url):
    return hashlib.md5(url.encode()).hexdigest()


# ==========================================
# SEEN JOBS TRACKER
# ==========================================

class SeenTracker:
    """Track already-scraped jobs to avoid duplicates"""

    def __init__(self, filepath='seen_jobs.json'):
        self.filepath = filepath
        self.seen = self._load()

    def _load(self):
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
            # Purge entries older than 60 days
            cutoff = (datetime.now() - timedelta(days=60)).isoformat()
            return {k: v for k, v in data.items() if v > cutoff}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save(self):
        with open(self.filepath, 'w') as f:
            json.dump(self.seen, f, indent=2)

    def is_seen(self, url):
        return job_uid(url) in self.seen

    def mark_seen(self, url):
        self.seen[job_uid(url)] = datetime.now().isoformat()

    def filter_new(self, urls):
        new = [u for u in urls if not self.is_seen(u)]
        return new


# ==========================================
# STEP 1: Collect job URLs from listing page
# ==========================================

def fetch_page(session, url):
    """Fetch a page with retry"""
    for attempt in range(3):
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            print(f"  ⚠ Attempt {attempt+1} failed for {url}: {e}")
            if attempt < 2:
                time.sleep(3)
    return None


def collect_job_urls(session):
    """
    Fetch job URLs from the listing page using Playwright (headless browser).
    SomaliJobs.com is a JavaScript SPA — the listing page only renders
    job links client-side, so we need a real browser to execute the JS.
    """
    print("🔍 Fetching job listing page (headless browser)...")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ⚠ Playwright not installed. Installing...")
        import subprocess, sys
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'playwright', '-q'])
        subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
        from playwright.sync_api import sync_playwright

    urls = []
    seen = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate to the jobs listing page
            page.goto('https://somalijobs.com/jobs', wait_until='networkidle', timeout=30000)

            # Wait for job listings to appear
            try:
                page.wait_for_selector('a[href*="/jobs/"]', timeout=10000)
            except:
                print("  ⚠ Timed out waiting for job links to load")

            # Scroll down a few times to load more jobs (lazy loading)
            for _ in range(5):
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(1500)

            # Scroll back to top
            page.evaluate('window.scrollTo(0, 0)')

            # Extract all job URLs
            job_pattern = re.compile(r'/jobs/[^/]+/\d+/')
            links = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
                    .filter(href => /\\/jobs\\/[^/]+\\/\\d+\\//.test(href));
            }''')

            # Filter and deduplicate
            skip_patterns = ['facebook.com', 'twitter.com', 'linkedin.com',
                             'whatsapp.com', 't.me', '/jobs/print/']

            for href in links:
                if any(s in href for s in skip_patterns):
                    continue
                clean_url = href.split('?')[0].split('#')[0]
                if clean_url not in seen:
                    seen.add(clean_url)
                    urls.append(clean_url)

            browser.close()

    except Exception as e:
        print(f"  ❌ Playwright error: {e}")
        print("  Falling back to Google search method...")
        urls = collect_job_urls_via_search(session)

    print(f"  📋 Found {len(urls)} job URLs")
    return urls


def collect_job_urls_via_search(session):
    """Fallback: discover job URLs via Google search if Playwright fails"""
    print("  🔍 Using Google search fallback to find job URLs...")
    urls = []
    seen = set()

    # Search for recent SomaliJobs pages
    search_queries = [
        'site:somalijobs.com/jobs/ 2026',
        'site:somalijobs.com/jobs/ 2025',
    ]

    for query in search_queries:
        try:
            resp = session.get(
                'https://www.google.com/search',
                params={'q': query, 'num': 50},
                timeout=15
            )
            # Extract somalijobs URLs from search results
            found = re.findall(r'https://somalijobs\.com/jobs/[^/]+/\d+/[^"&\s]+', resp.text)
            for url in found:
                clean = url.split('&')[0].split('"')[0]
                if clean not in seen:
                    seen.add(clean)
                    urls.append(clean)
        except Exception as e:
            print(f"    ⚠ Search failed: {e}")

    return urls


# ==========================================
# STEP 2: Scrape a single job detail page
# ==========================================

def scrape_job_page(session, url):
    """Fetch a job page and extract all fields from JSON-LD + HTML"""
    html = fetch_page(session, url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Decode Cloudflare-obfuscated emails before extracting content
    deobfuscate_emails(soup)

    job = {
        'title': '',
        'organization': '',
        'location': location_from_url(url),
        'country': '',
        'description': '',
        'url': url,
        'deadline': '',
        'datePosted': '',
        'sector': '',
        'source': 'somalijobs',
        'type': '',
        'experience': '',
        'howToApply': '',
        'qualifications': '',
        'responsibilities': '',
    }

    # --- Method 1: JSON-LD structured data (most reliable) ---
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get('@type') == 'JobPosting' or 'datePosted' in item:
                    job['title'] = item.get('title', '') or job['title']
                    job['datePosted'] = item.get('datePosted', '') or job['datePosted']
                    job['deadline'] = item.get('validThrough', '') or job['deadline']
                    org = item.get('hiringOrganization', {})
                    if org.get('name'):
                        job['organization'] = org['name']
                    loc = item.get('jobLocation', {}).get('address', {})
                    loc_name = loc.get('addressLocality', '')
                    if loc_name:
                        job['location'] = prettify_location(loc_name)
                    emp_type = item.get('employmentType', '')
                    if emp_type and emp_type != 'Organization':
                        job['type'] = emp_type
        except (json.JSONDecodeError, AttributeError):
            pass

    # --- Method 2: Regex on raw HTML for JSON-LD (fallback for SPAs) ---
    if not job['organization']:
        m = re.search(r'"hiringOrganization"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', html)
        if m:
            job['organization'] = m.group(1)
    if not job['datePosted']:
        m = re.search(r'"datePosted"\s*:\s*"([^"]+)"', html)
        if m:
            job['datePosted'] = m.group(1)
    if not job['deadline']:
        m = re.search(r'"validThrough"\s*:\s*"([^"]+)"', html)
        if m:
            job['deadline'] = m.group(1)

    # --- Method 3: HTML heading ---
    h1 = soup.find('h1')
    if h1:
        job['title'] = clean_text(h1.get_text().strip())

    # --- Method 4: Company link ---
    if not job['organization']:
        for link in soup.find_all('a', href=re.compile(r'/company/')):
            text = link.get_text().strip()
            if text and len(text) > 1 and 'See company' not in text:
                job['organization'] = text
                break

    # --- Method 5: Extract sections by h2 headings ---
    for h2 in soup.find_all('h2'):
        heading = h2.get_text().strip().lower()
        content = collect_section(h2)

        if 'job description' in heading or heading == 'description':
            job['description'] = content
        elif 'skills' in heading or 'qualifications' in heading or 'requirements' in heading:
            job['qualifications'] = content
        elif 'responsibilities' in heading or 'duties' in heading:
            job['responsibilities'] = content
        elif 'how to apply' in heading or 'application' in heading:
            job['howToApply'] = content
            # Also grab apply link
            next_el = h2.find_next_sibling()
            if next_el:
                apply_link = next_el.find('a', href=True)
                if apply_link and 'somalijobs.com' not in apply_link['href']:
                    job['howToApply'] += '\n\nApply at: ' + apply_link['href']
        elif 'job details' in heading:
            parse_job_details_section(h2, job)

    # --- Fallback: Value-above-label from body text ---
    body_text = soup.get_text()
    body_lines = [l.strip() for l in body_text.split('\n') if l.strip()]
    label_map = {
        'posted date': 'datePosted', 'expire date': 'deadline',
        'deadline': 'deadline', 'closing date': 'deadline',
        'category': 'sector', 'location': 'location',
        'job type': 'type', 'experience level': 'experience',
    }
    for i in range(1, len(body_lines)):
        line_lower = body_lines[i].lower()
        for label, field in label_map.items():
            if line_lower == label:
                value = body_lines[i - 1]
                if value and len(value) < 100 and not job.get(field):
                    if field == 'location':
                        job[field] = prettify_location(value)
                    else:
                        job[field] = value
                break

    # Inline deadline fallback
    if not job['deadline']:
        m = re.search(r'(?:Deadline|Closing\s*Date)[:\s]*([A-Z][a-z]+[\s,]+\d{1,2}[\s,]+\d{4})', body_text, re.I)
        if m:
            job['deadline'] = m.group(1).strip()

    # --- Combine description ---
    full_desc = job['description'] or ''
    if job['qualifications']:
        full_desc += '\n\n=== Skills & Qualifications ===\n' + job['qualifications']
    if job['responsibilities']:
        full_desc += '\n\n=== Responsibilities ===\n' + job['responsibilities']
    job['description'] = clean_text(full_desc.strip()[:3000])

    # Fix type
    if not job['type'] or job['type'] == 'Organization':
        job['type'] = 'Full Time'

    # Set country
    job['country'] = detect_country(job['location'])

    # Clean all text fields
    for key in ['title', 'organization', 'description', 'qualifications',
                'responsibilities', 'howToApply', 'sector', 'experience']:
        job[key] = clean_text(job.get(key, ''))

    return job


def location_from_url(url):
    m = re.search(r'/jobs/([^/]+)/', url)
    return prettify_location(m.group(1)) if m else ''


def collect_section(h2):
    """Collect text content after an h2 until the next h2/h1"""
    content = []
    el = h2.find_next_sibling()
    social_names = {'facebook', 'twitter', 'linkedin', 'whatsapp', 'telegram', 'print',
                    'twitter(x)', 'open_in_new'}

    while el and el.name not in ('h1', 'h2'):
        text = el.get_text().strip()
        if 'Similar Jobs' in text or el.name == 'footer':
            break
        if text.lower() in social_names:
            el = el.find_next_sibling()
            continue
        if text:
            content.append(text)
        el = el.find_next_sibling()

    return clean_text('\n'.join(content).strip()[:2000])


def parse_job_details_section(h2, job):
    """Parse the Job Details grid (value-above-label pattern)"""
    lines = []
    el = h2.find_next_sibling()

    while el and el.name not in ('h1', 'h2'):
        if el.name == 'footer' or 'Similar Jobs' in (el.get_text() or ''):
            break
        text = el.get_text().strip()
        if text:
            for line in text.split('\n'):
                l = line.strip()
                if l:
                    lines.append(l)
        el = el.find_next_sibling()

    label_map = {
        'posted date': 'datePosted', 'posted': 'datePosted',
        'expire date': 'deadline', 'expire': 'deadline',
        'deadline': 'deadline', 'closing date': 'deadline',
        'category': 'sector', 'location': 'location',
        'job type': 'type', 'employment type': 'type',
        'experience level': 'experience', 'experience': 'experience',
    }

    for i in range(len(lines)):
        line_lower = lines[i].lower().strip()
        for label_key, field_name in label_map.items():
            if line_lower == label_key or line_lower == label_key + ':':
                if i > 0:
                    value = lines[i - 1].strip()
                    if value and len(value) < 100:
                        if field_name == 'location':
                            job[field_name] = prettify_location(value)
                        else:
                            job[field_name] = value
                break


# ==========================================
# MAIN SCRAPE FUNCTION
# ==========================================

def scrape_somalijobs(seen_tracker=None):
    """
    Full scrape pipeline:
    1. Collect job URLs from listing page
    2. Filter out already-seen jobs
    3. Fetch each new job page for full details
    4. Return list of job dicts
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # Step 1: Collect URLs
    all_urls = collect_job_urls(session)
    if not all_urls:
        return []

    # Step 2: Filter to new jobs only
    if seen_tracker:
        new_urls = seen_tracker.filter_new(all_urls)
        print(f"  🆕 {len(new_urls)} new jobs (of {len(all_urls)} total)")
    else:
        new_urls = all_urls

    if not new_urls:
        print("  ✅ No new jobs to scrape")
        return []

    # Limit
    urls_to_scrape = new_urls[:MAX_JOBS]

    # Step 3: Scrape each job page
    jobs = []
    total = len(urls_to_scrape)
    print(f"\n📄 Scraping {total} job pages...")

    for i, url in enumerate(urls_to_scrape):
        job = scrape_job_page(session, url)
        if job and job['title']:
            jobs.append(job)

            # Mark as seen
            if seen_tracker:
                seen_tracker.mark_seen(url)

        if (i + 1) % 10 == 0 or i == total - 1:
            print(f"  ... {i+1}/{total} done")

        time.sleep(REQUEST_DELAY)

    # Save seen tracker
    if seen_tracker:
        seen_tracker.save()

    print(f"\n✅ Scraped {len(jobs)} jobs successfully")
    return jobs
