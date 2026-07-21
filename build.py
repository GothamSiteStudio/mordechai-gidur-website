import json
import re
from pathlib import Path


def read_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


SITE = "https://mordechaigidur.co.il"


def service_url(filename: str) -> str:
    """Clean, root-relative URL for a service page (no .html). e.g. iskurit.html -> /services/iskurit"""
    name = filename[:-5] if filename.endswith(".html") else filename
    return f"/services/{name}"


def city_url(filename: str) -> str:
    """Clean, root-relative URL for a city page (no .html). e.g. tel-aviv.html -> /service-areas/tel-aviv"""
    name = filename[:-5] if filename.endswith(".html") else filename
    return f"/service-areas/{name}"


def post_url(slug: str) -> str:
    """Clean, root-relative URL for a blog post (no .html)."""
    return f"/blog/{slug}"


# ---------- Contextual internal auto-linking ----------
# The first mention of a topic inside real body prose becomes a descriptive link to that
# topic's page. Deliberately conservative: never inside an existing <a>, never inside a
# heading/summary/caption, never inside a tag or attribute, at most one link per target
# per page and at most AUTOLINK_LIMIT links added per page.
_HEB = "א-ת"
AUTOLINK_LIMIT = 5

LINK_TOPICS = [
    ("/services/iskurit", ["גדר איסכורית", "גדרות איסכורית", "גידור איסכורית", "גדר פח", "איסכורית"]),
    ("/services/panel", ["גדר פאנל", "גדרות פאנל", "גידור פאנל", "פאנלים מודולריים"]),
    ("/services/reshet", ["גדר רשת", "גדרות רשת"]),
    ("/services/temporary-fencing", ["השכרת גדרות", "השכרת גדר", "גידור זמני", "גדר זמנית"]),
    ("/services/gates", ["שערים לאתרי בנייה", "שערים לאתרי בניה", "שערי הזזה", "שער הזזה",
                         "מחסום זרוע", "שערים"]),
    ("/services/passages", ["מעברי הולכי רגל", "מעבר להולכי רגל", "מעברים בטוחים",
                            "מעבר מקורה", "מנהרת מעבר"]),
    ("/services/tree-protection", ["הגנת עצים", "הגנה על עצים", "כלובי הגנה", "כלוב הגנה"]),
    ("/services/branding", ["מיתוג גדרות", "מיתוג הגדר", "מיתוג גדר", "חיפוי יוטה"]),
    ("/services/signage", ["שילוט בטיחות", "שילוט אזהרה", "שלטי אזהרה", "שילוט תקני", "שילוט"]),
    ("/blog/gidur-price-guide", ["כמה עולה גידור", "עלות הגידור", "מחיר הגידור",
                                 "מחירי הגידור", "מחירי גידור", "עלויות הגידור"]),
    ("/blog/construction-fencing-law", ["תקנות הבטיחות בעבודה", "תקנות הבטיחות",
                                        "חובת הגידור", "חובת גידור", "דרישות החוק"]),
    ("/blog/fencing-standards-safety", ["תקני הבטיחות", "תקני בטיחות", "עמידה בתקנים",
                                        "התקנים הישראליים"]),
    ("/blog/safety-signage-construction", ["שילוט חובה", "שלטי בטיחות"]),
    ("/blog/temporary-mesh-fence", ["גדר רשת זמנית", "גדרות רשת ניידות"]),
    ("/blog/iskurit-vs-panel", ["איסכורית או פאנל", "בחירת סוג הגדר"]),
]

_AUTOLINK_SKIP_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "summary", "th", "figcaption")
_TAG_RE = re.compile(r"<[^>]*>")


def _autolink_text(text, patterns, added, limit):
    """Link the first eligible mention inside one plain-text node."""
    if not text.strip():
        return text
    out = ""
    cursor = 0
    while len(added) < limit:
        best = None
        for url, pat in patterns.items():
            if url in added:
                continue
            m = pat.search(text, cursor)
            if m is None:
                continue
            if (best is None or m.start() < best[0].start()
                    or (m.start() == best[0].start() and len(m.group(0)) > len(best[0].group(0)))):
                best = (m, url)
        if best is None:
            break
        m, url = best
        out += text[cursor:m.start()] + f'<a href="{url}">{m.group(0)}</a>'
        cursor = m.end()
        added.append(url)
    return out + text[cursor:]


_HREF_RE = re.compile(r'<a\b[^>]*?href\s*=\s*"([^"#?]*)', re.I)


def existing_links(*html_blocks):
    """Internal hrefs already present in the given HTML — so we never link the same
    target twice on one page (some JSON prose already carries hand-written links)."""
    found = set()
    for block in html_blocks:
        if block:
            found.update(h.rstrip("/") or "/" for h in _HREF_RE.findall(block) if h.startswith("/"))
    return found


def autolink(html: str, self_url: str = "", skip_urls=(), limit: int = AUTOLINK_LIMIT):
    """Add first-mention contextual links to a block of already-rendered body prose."""
    skip = {u.rstrip("/") or "/" for u in skip_urls} | set(skip_urls)
    skip |= existing_links(html)
    topics = [(u, ph) for u, ph in LINK_TOPICS if u != self_url and u not in skip]
    if not topics or limit <= 0:
        return html
    # The Hebrew-letter guards must wrap the WHOLE alternation, otherwise a longer
    # alternative can match mid-word (e.g. "שילוט בטיחות" inside "שילוט בטיחותי") and
    # the anchor would cut a word in half.
    patterns = {
        url: re.compile(f"(?<![{_HEB}])(?:"
                        + "|".join(re.escape(p) for p in sorted(phrases, key=len, reverse=True))
                        + f")(?![{_HEB}])")
        for url, phrases in topics
    }

    parts = []
    added = []
    a_depth = 0
    skip_depth = 0
    pos = 0
    for m in _TAG_RE.finditer(html):
        chunk = html[pos:m.start()]
        parts.append(_autolink_text(chunk, patterns, added, limit)
                     if (a_depth == 0 and skip_depth == 0) else chunk)
        tag = m.group(0)
        parts.append(tag)
        name = re.match(r"</?\s*([a-zA-Z0-9]+)", tag)
        if name and not tag.endswith("/>"):
            n = name.group(1).lower()
            closing = tag.startswith("</")
            if n == "a":
                a_depth = max(0, a_depth + (-1 if closing else 1))
            elif n in _AUTOLINK_SKIP_TAGS:
                skip_depth = max(0, skip_depth + (-1 if closing else 1))
        pos = m.end()
    tail = html[pos:]
    parts.append(_autolink_text(tail, patterns, added, limit)
                 if (a_depth == 0 and skip_depth == 0) else tail)
    return "".join(parts)


def _render_link_list(links, indent=8, icon="fas fa-link"):
    """links = [{"url", "label", "note"?}] -> styled <ul class="article-list">."""
    if not links:
        return ""
    pad = " " * indent
    parts = [f'{pad}<ul class="article-list">']
    for link in links:
        note = f' — {link["note"]}' if link.get("note") else ""
        parts.append(f'{pad}    <li><i class="{icon}" aria-hidden="true"></i> '
                     f'<a href="{link["url"]}">{link["label"]}</a>{note}</li>')
    parts.append(f"{pad}</ul>")
    return "\n".join(parts)


# ---------- Shared content blocks (tables, figures) ----------
def _render_table(table, indent=8):
    """Render a styled data table. table = {"headers": [...], "rows": [[...], ...]}"""
    pad = " " * indent
    inner = pad + "    "
    parts = [f'{pad}<div class="table-wrap">', f'{inner}<table class="article-table">']
    headers = table.get("headers", [])
    if headers:
        parts.append(f'{inner}    <thead><tr>' + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead>")
    parts.append(f'{inner}    <tbody>')
    for row in table.get("rows", []):
        parts.append(f'{inner}        <tr>' + "".join(f"<td>{c}</td>" for c in row) + "</tr>")
    parts.append(f'{inner}    </tbody>')
    parts.append(f'{inner}</table>')
    parts.append(f'{pad}</div>')
    return "\n".join(parts)


def _render_figure(image, indent=8):
    """Render a content image. image = {"src", "alt", "title"?, "caption"?}"""
    pad = " " * indent
    title = image.get("title", image["alt"])
    caption = image.get("caption")
    parts = [f'{pad}<figure class="article-figure">',
             f'{pad}    <img src="{image["src"]}" alt="{image["alt"]}" title="{title}" loading="lazy" decoding="async">']
    if caption:
        parts.append(f'{pad}    <figcaption>{caption}</figcaption>')
    parts.append(f'{pad}</figure>')
    return "\n".join(parts)


def _render_hero_figure(image, indent=24):
    """Above-the-fold service hero image: explicit dimensions, high fetch priority, no lazy loading."""
    if not image:
        return ""
    pad = " " * indent
    title = image.get("title", image["alt"])
    caption = image.get("caption")
    dims = ""
    if image.get("width") and image.get("height"):
        dims = f' width="{image["width"]}" height="{image["height"]}"'
    parts = [f'{pad}<figure class="article-figure service-hero-figure">',
             f'{pad}    <img src="{image["src"]}" alt="{image["alt"]}" title="{title}"{dims} fetchpriority="high" decoding="async">']
    if caption:
        parts.append(f'{pad}    <figcaption>{caption}</figcaption>')
    parts.append(f'{pad}</figure>')
    return "\n".join(parts)


def _hero_preload(src):
    """Preload tag for the page's LCP image; empty when the page has no hero image."""
    if not src:
        return ""
    return f'    <link rel="preload" as="image" href="{src}" fetchpriority="high">'


# ---------- City page content blocks (enriched local content) ----------
def _render_city_sections(sections, indent=8):
    pad = " " * indent
    html = []
    for s in sections:
        html.append(f'{pad}<h2>{s["heading"]}</h2>')
        for p in s.get("paragraphs", []):
            html.append(f'{pad}<p>{p}</p>')
        if s.get("list"):
            html.append(f'{pad}<ul class="article-list">')
            for it in s["list"]:
                html.append(f'{pad}    <li><i class="fas fa-check" aria-hidden="true"></i> {it}</li>')
            html.append(f'{pad}</ul>')
        if s.get("table"):
            html.append(_render_table(s["table"], indent))
        if s.get("image"):
            html.append(_render_figure(s["image"], indent))
    return "\n".join(html)


def _render_city_recommended(recommended, city_name, indent=8):
    if not recommended:
        return ""
    pad = " " * indent
    parts = [f'{pad}<h2>שירותי הגידור המומלצים ב{city_name}</h2>',
             f'{pad}<ul class="article-list">']
    for r in recommended:
        parts.append(
            f'{pad}    <li><i class="fas fa-check" aria-hidden="true"></i> '
            f'<a href="{service_url(r["filename"])}"><strong>{r["label"]}</strong></a> — {r["reason"]}</li>'
        )
    parts.append(f'{pad}</ul>')
    return "\n".join(parts)


def _render_city_faq(faq, indent=8):
    if not faq:
        return ""
    pad = " " * indent
    parts = [f'{pad}<h2>שאלות נפוצות: גידור אתרי בנייה</h2>', f'{pad}<div class="blog-faq">']
    for f in faq:
        parts.append(f'{pad}    <details class="blog-faq-item">')
        parts.append(f'{pad}        <summary>{f["q"]}</summary>')
        parts.append(f'{pad}        <div class="blog-faq-answer"><p>{f["a"]}</p></div>')
        parts.append(f'{pad}    </details>')
    parts.append(f'{pad}</div>')
    return "\n".join(parts)


def _city_faq_schema(faq):
    if not faq:
        return ""
    import json as _json
    block = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in faq
        ],
    }
    return ('    <script type="application/ld+json">\n    '
            + _json.dumps(block, ensure_ascii=False, indent=4).replace("\n", "\n    ")
            + "\n    </script>")


def _nearby_cities(pages, index, count=5):
    """Cities to cross-link from the page at `index`: same region first, then a stable
    round-robin over the rest so every city receives a comparable number of inbound links."""
    page = pages[index]
    picked = [p for i, p in enumerate(pages)
              if i != index and p["region"] == page["region"]][:count]
    picked_names = {p["filename"] for p in picked}
    step = 1
    while len(picked) < count and step < len(pages):
        cand = pages[(index + step) % len(pages)]
        if cand["filename"] != page["filename"] and cand["filename"] not in picked_names:
            picked.append(cand)
            picked_names.add(cand["filename"])
        step += 1
    return picked[:count]


def _render_nearby_cities(pages, index, indent=8):
    page = pages[index]
    near = _nearby_cities(pages, index)
    if not near:
        return ""
    pad = " " * indent
    same_region = any(c["region"] == page["region"] for c in near)
    if same_region:
        heading = f'אזורי שירות נוספים בסביבת {page["city_name"]}'
        lead = ('הצוותים שלנו עובדים גם ביישובים הסמוכים, ולעיתים קרובות באותו שבוע עבודה. '
                'אם הפרויקט שלכם מתפרס על יותר מאתר אחד, נשמח לתאם גידור לכולם יחד:')
    else:
        heading = "אזורי שירות נוספים ברחבי הארץ"
        lead = (f'מעבר ל{page["city_name"]} אנחנו מגדרים אתרי בנייה בכל הארץ. '
                'אם יש לכם פרויקטים נוספים ביישובים אחרים, אפשר לתאם את כולם מול אותו צוות:')
    links = [{"url": city_url(c["filename"]),
              "label": f'גידור אתרי בנייה ב{c["city_name"]}',
              "note": c["region"]} for c in near]
    return (f"{pad}<h2>{heading}</h2>\n{pad}<p>{lead}</p>\n"
            + _render_link_list(links, indent, icon="fas fa-map-marker-alt"))


def _render_city_related_posts(posts, index, count=3, indent=8):
    """Three guides per city page, rotated so all posts get inbound links."""
    if not posts:
        return ""
    pad = " " * indent
    chosen = [posts[(index * count + k) % len(posts)] for k in range(min(count, len(posts)))]
    links = [{"url": post_url(p["slug"]), "label": p["title"], "note": p["read_time"]}
             for p in chosen]
    return (f'{pad}<h2>מדריכים שיעזרו לכם לבחור</h2>\n'
            f'{pad}<p>ריכזנו בבלוג מדריכים מקצועיים שמסבירים איך בוחרים גדר, מה עולה גידור אתר '
            f'ומה מחייבות התקנות. שווה לקרוא לפני שסוגרים ספק:</p>\n'
            + _render_link_list(links, indent, icon="fas fa-book-open"))


def _render_city_helpful_links(city_name, indent=8):
    # NB: /service-areas/ is deliberately absent — the breadcrumb at the top of every
    # city page already links it, and we keep to one link per target per page.
    pad = " " * indent
    links = [
        {"url": "/services/", "label": "כל שירותי הגידור שלנו",
         "note": "איסכורית, פאנל, רשת, שערים, מעברים, מיתוג ושילוט"},
        {"url": "/blog/", "label": "הבלוג — מדריכים ומידע מקצועי",
         "note": "מחירים, תקנים, בטיחות ובחירת סוג גדר"},
    ]
    return (f'{pad}<h2>קישורים שימושיים</h2>\n'
            f'{pad}<p>לפני שמזמינים גידור ב{city_name} כדאי להשוות בין הפתרונות ולוודא '
            f'שהאתר עומד בדרישות. שלושת העמודים האלה מרכזים את כל מה שצריך:</p>\n'
            + _render_link_list(links, indent))


# ---------- City pages ----------
def build_city_pages():
    pages = read_json("data.json")
    posts = sorted(read_json("data_blog.json"), key=lambda p: p["date"], reverse=True)
    template = Path("template_city.html").read_text(encoding="utf-8")
    output_dir = Path("service-areas")
    output_dir.mkdir(exist_ok=True)

    for index, page in enumerate(pages):
        canonical = f"{SITE}/service-areas/{page['filename'][:-5]}"
        faq = page.get("faq", [])
        recommended = page.get("recommended", [])
        extra_sections = _render_city_sections(page.get("sections", []))
        recommended_block = _render_city_recommended(recommended, page["city_name"])
        faq_block = _render_city_faq(faq)
        faq_schema = _city_faq_schema(faq)
        nearby_cities = _render_nearby_cities(pages, index)
        related_posts = _render_city_related_posts(posts, index)
        helpful_links = _render_city_helpful_links(page["city_name"])
        # Keep to one link per target per page: anything the curated blocks on this page
        # already link must not be auto-linked again in the prose.
        curated = existing_links(recommended_block, nearby_cities, related_posts,
                                 helpful_links, faq_block)
        # Only show the CTA once the page actually has enriched content below the intro.
        cta_block = CTA_BOX if (page.get("sections") or faq) else ""

        # Contextual first-mention links across the page's own prose (intro + sections).
        prose = autolink(
            f'<p>{page["unique_paragraph_1"]}</p>\n<p>{page["unique_paragraph_2"]}</p>\n'
            + extra_sections,
            skip_urls=curated,
        )
        para_1, rest = prose.split("</p>\n", 1)
        para_2, extra_sections = rest.split("</p>\n", 1)
        unique_paragraph_1 = para_1[3:]
        unique_paragraph_2 = para_2[3:]

        new_content = template
        new_content = new_content.replace("{extra_sections}", extra_sections)
        new_content = new_content.replace("{recommended_block}", recommended_block)
        new_content = new_content.replace("{nearby_cities}", nearby_cities)
        new_content = new_content.replace("{related_posts}", related_posts)
        new_content = new_content.replace("{helpful_links}", helpful_links)
        new_content = new_content.replace("{faq_block}", faq_block)
        new_content = new_content.replace("{cta_block}", cta_block)
        new_content = new_content.replace("{faq_schema}", faq_schema)
        new_content = new_content.replace("{canonical}", canonical)
        new_content = new_content.replace("{city_name}", page["city_name"])
        new_content = new_content.replace("{region}", page["region"])
        new_content = new_content.replace("{seo_desc_start}", page["seo_desc_start"])
        new_content = new_content.replace("{unique_paragraph_1}", unique_paragraph_1)
        new_content = new_content.replace("{unique_paragraph_2}", unique_paragraph_2)

        filename = output_dir / page["filename"]
        write_file(filename, new_content)
        print(f"Created city page: {filename}")


# ---------- Service pages ----------
def _render_links(items, indent=0, exclude=None):
    pad = " " * indent
    lines = []
    for item in items:
        if exclude and item["filename"] == exclude:
            continue
        lines.append(f'{pad}<li><a href="{service_url(item["filename"])}">{item["service_name"]}</a></li>')
    return "\n".join(lines)


def _render_benefits(items, indent=0):
    pad = " " * indent
    return "\n".join(f'{pad}<li><i class="fas fa-check" aria-hidden="true"></i> {text}</li>' for text in items)


def _render_list(items, indent=0):
    pad = " " * indent
    return "\n".join(f"{pad}<li>{text}</li>" for text in items)


def _render_specs(items, indent=0):
    pad = " " * indent
    row_pad = pad + "    "
    rows = []
    for spec in items:
        rows.append(
            f"""{pad}<div class="spec-row">
{row_pad}<span class="spec-label">{spec["label"]}</span>
{row_pad}<span class="spec-value">{spec["value"]}</span>
{pad}</div>"""
        )
    return "\n".join(rows)


def _render_related(items, indent=0):
    pad = " " * indent
    card_pad = pad + "    "
    cards = []
    for rel in items:
        cards.append(
            f"""{pad}<a href="{service_url(rel["filename"])}" class="related-service-card">
{card_pad}<i class="{rel["icon"]}" aria-hidden="true"></i>
{card_pad}<h4>{rel["title"]}</h4>
{pad}</a>"""
        )
    return "\n".join(cards)


def _render_service_city_links(svc, cities, index, per_service=10, indent=16):
    """Service -> city cross-links, rotated so all 20 cities are covered across the services."""
    if not cities:
        return ""
    pad = " " * indent
    offset = (index * per_service) % len(cities)
    chosen = [cities[(offset + k) % len(cities)] for k in range(min(per_service, len(cities)))]
    name = svc["service_name"]
    links = [{"url": city_url(c["filename"]), "label": f'{name} ב{c["city_name"]}',
              "note": c["region"]} for c in chosen]
    return f"""{pad}<h2 class="section-title">{name} בכל רחבי הארץ</h2>
{pad}<p>אנחנו מספקים {name} לאתרי בנייה בפריסה ארצית, עם צוותי התקנה שמגיעים לאתר בהתראה קצרה.
{pad}    אלה חלק מהיישובים שבהם אנחנו עובדים באופן שוטף:</p>
{_render_link_list(links, indent, icon="fas fa-map-marker-alt")}
{pad}<p>לא מצאתם את היישוב שלכם? ריכזנו את הרשימה המלאה בעמוד <a href="/service-areas/">אזורי השירות</a>,
{pad}    ולמידע מקצועי לפני קבלת החלטה כדאי לעיין ב<a href="/blog/">בלוג המקצועי</a> שלנו.</p>"""


def build_service_pages():
    services = read_json("data_services.json")
    cities = read_json("data.json")
    template = Path("template_service.html").read_text(encoding="utf-8")
    output_dir = Path("services")
    output_dir.mkdir(exist_ok=True)

    primary_menu = [s for s in services if s.get("menu_group") == "primary"]
    secondary_menu = [s for s in services if s.get("menu_group") != "primary"]
    footer_services = services[:6]

    for svc_index, svc in enumerate(services):
        menu_primary_links = _render_links(primary_menu, indent=32)
        menu_secondary_links = _render_links(secondary_menu, indent=32)
        benefits_list = _render_benefits(svc["benefits"], indent=24)
        uses_list = _render_list(svc["uses"], indent=24)
        spec_rows = _render_specs(svc["specs"], indent=28)
        sidebar_links = _render_links(services, indent=28, exclude=svc["filename"])
        footer_service_links = _render_links(footer_services, indent=24)
        related_cards = _render_related(svc["related"], indent=20)
        # Optional enriched content + FAQ (durable, JSON-driven; mirrors city pages).
        extra_sections = _render_city_sections(svc.get("sections", []))
        faq_block = _render_city_faq(svc.get("faq", []))
        faq_schema = _city_faq_schema(svc.get("faq", []))
        hero_image = svc.get("hero_image")
        hero_figure = _render_hero_figure(hero_image)
        hero_preload = _hero_preload(hero_image["src"] if hero_image else "")
        city_links = _render_service_city_links(svc, cities, svc_index)

        # One link per target per page: skip the page itself and whatever the curated
        # blocks on this page (related cards, city links, FAQ) already link to.
        self_url = service_url(svc["filename"])
        curated = existing_links(related_cards, city_links, faq_block) | {"/services/"}
        prose = autolink(
            f'<p>{svc["intro_paragraph"]}</p>\n<p>{svc["uses_intro"]}</p>\n' + extra_sections,
            self_url=self_url, skip_urls=curated,
        )
        para_1, rest = prose.split("</p>\n", 1)
        para_2, extra_sections = rest.split("</p>\n", 1)
        intro_paragraph = para_1[3:]
        uses_intro = para_2[3:]

        replacements = {
            "{city_links}": city_links,
            "{hero_figure}": hero_figure,
            "{hero_preload}": hero_preload,
            "{extra_sections}": extra_sections,
            "{faq_block}": faq_block,
            "{faq_schema}": faq_schema,
            "{meta_title}": svc["meta_title"],
            "{meta_description}": svc["meta_description"],
            "{meta_keywords}": svc["meta_keywords"],
            "{canonical}": svc["canonical"],
            "{service_name}": svc["service_name"],
            "{schema_description}": svc["schema_description"],
            "{hero_title}": svc["hero_title"],
            "{hero_subtitle}": svc["hero_subtitle"],
            "{intro_heading}": svc["intro_heading"],
            "{intro_paragraph}": intro_paragraph,
            "{benefits_heading}": svc["benefits_heading"],
            "{benefits_list}": benefits_list,
            "{uses_heading}": svc["uses_heading"],
            "{uses_intro}": uses_intro,
            "{uses_list}": uses_list,
            "{specs_heading}": svc["specs_heading"],
            "{spec_rows}": spec_rows,
            "{cta_heading}": svc["cta_heading"],
            "{cta_text}": svc["cta_text"],
            "{related_heading}": svc["related_heading"],
            "{related_cards}": related_cards,
            "{menu_primary_links}": menu_primary_links,
            "{menu_secondary_links}": menu_secondary_links,
            "{sidebar_links}": sidebar_links,
            "{footer_service_links}": footer_service_links,
        }

        new_content = template
        for placeholder, value in replacements.items():
            new_content = new_content.replace(placeholder, value)

        filename = output_dir / svc["filename"]
        write_file(filename, new_content)
        print(f"Created service page: {filename}")


# ---------- Blog ----------
def _render_article_sections(sections):
    html = []
    for s in sections:
        html.append(f'                    <h2>{s["heading"]}</h2>')
        for p in s["paragraphs"]:
            html.append(f'                    <p>{p}</p>')
        if s.get("list"):
            html.append('                    <ul class="article-list">')
            for it in s["list"]:
                html.append(f'                        <li><i class="fas fa-check" aria-hidden="true"></i> {it}</li>')
            html.append('                    </ul>')
        if s.get("table"):
            html.append(_render_table(s["table"], indent=20))
        if s.get("image"):
            html.append(_render_figure(s["image"], indent=20))
    return "\n".join(html)


def _render_faq(faq):
    if not faq:
        return ""
    parts = ['                    <h2>שאלות נפוצות</h2>', '                    <div class="blog-faq">']
    for f in faq:
        parts.append('                        <details class="blog-faq-item">')
        parts.append(f'                            <summary>{f["q"]}</summary>')
        parts.append(f'                            <div class="blog-faq-answer"><p>{f["a"]}</p></div>')
        parts.append('                        </details>')
    parts.append('                    </div>')
    return "\n".join(parts)


def _render_sources(sources):
    if not sources:
        return ""
    parts = [
        '                    <h2>מקורות ולמידע נוסף</h2>',
        '                    <p class="sources-note">המידע הרגולטורי במאמר מבוסס על המקורות הרשמיים הבאים. אין באמור תחליף לייעוץ בטיחות פרטני או לעיון בנוסח המחייב של התקנות:</p>',
        '                    <ul class="article-list">',
    ]
    for s in sources:
        parts.append(
            f'                        <li><i class="fas fa-external-link-alt" aria-hidden="true"></i> '
            f'<a href="{s["url"]}" target="_blank" rel="nofollow noopener">{s["name"]}</a></li>'
        )
    parts.append('                    </ul>')
    return "\n".join(parts)


def _render_related_sidebar(related):
    links = "\n".join(
        f'                        <li><a href="{r["url"]}">{r["name"]}</a></li>' for r in related
    )
    return links


def _post_schema(post, url):
    blocks = [{
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post["title"],
        "description": post["excerpt"],
        "image": f"{SITE}/pictures/{post['image']}",
        "datePublished": post["date"],
        "dateModified": post.get("date_modified", post["date"]),
        "author": {"@type": "Organization", "name": "מרדכי סיונוב גידור אתרי בניה", "url": f"{SITE}/"},
        "publisher": {
            "@type": "Organization",
            "name": "מרדכי סיונוב גידור אתרי בניה",
            "logo": {"@type": "ImageObject", "url": f"{SITE}/logo.svg"},
        },
        "mainEntityOfPage": url,
    }]
    if post.get("faq"):
        blocks.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": f["q"],
                 "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                for f in post["faq"]
            ],
        })
    import json as _json
    return "\n".join(
        '    <script type="application/ld+json">\n    '
        + _json.dumps(b, ensure_ascii=False, indent=4).replace("\n", "\n    ")
        + "\n    </script>"
        for b in blocks
    )


CTA_BOX = """                    <div class="cta-box">
                        <h3>צריכים גידור לאתר הבנייה שלכם?</h3>
                        <p>נשמח לייעץ ולהכין הצעת מחיר מותאמת, ללא התחייבות.</p>
                        <div class="cta-buttons">
                            <a href="tel:0507575570" class="btn btn-primary"><i class="fas fa-phone-alt" aria-hidden="true"></i> 050-757-5570</a>
                            <a href="https://wa.me/972507575570" class="btn btn-secondary-dark" target="_blank"><i class="fab fa-whatsapp" aria-hidden="true"></i> וואטסאפ</a>
                        </div>
                    </div>"""


def _render_post_city_sidebar(cities, index, count=4):
    """Blog post -> city cross-links, rotated so the posts spread across the city cluster."""
    if not cities:
        return ""
    chosen = [cities[(index * count + k) % len(cities)] for k in range(min(count, len(cities)))]
    links = "\n".join(
        f'                            <li><a href="{city_url(c["filename"])}">'
        f'גידור אתרי בנייה ב{c["city_name"]}</a></li>' for c in chosen
    )
    return f"""                    <div class="sidebar-box">
                        <h4>אזורי שירות</h4>
                        <ul class="sidebar-links">
{links}
                            <li><a href="/service-areas/">כל אזורי השירות בארץ</a></li>
                        </ul>
                    </div>
"""


def _render_post_related_posts(posts, index, count=3):
    """Related-articles module — the site had none, so every post sat at ~1 inbound link."""
    if len(posts) < 2:
        return ""
    chosen = [posts[(index + k) % len(posts)] for k in range(1, min(count, len(posts) - 1) + 1)]
    links = "\n".join(
        f'                            <li><a href="{post_url(p["slug"])}">{p["title"]}</a></li>'
        for p in chosen
    )
    return f"""                    <div class="sidebar-box">
                        <h4>מאמרים נוספים בבלוג</h4>
                        <ul class="sidebar-links">
{links}
                        </ul>
                    </div>
"""


def _build_post_content(post, posts=None, cities=None, index=0):
    posts = posts or [post]
    cities = cities or []
    self_url = post_url(post["slug"])
    faq = _render_faq(post.get("faq"))
    sources = _render_sources(post.get("sources"))
    related = _render_related_sidebar(post["related_services"])
    city_box = _render_post_city_sidebar(cities, index)
    posts_box = _render_post_related_posts(posts, index)
    curated = existing_links(related, city_box, posts_box, faq)
    sections = autolink(_render_article_sections(post["sections"]),
                        self_url=self_url, skip_urls=curated)
    img = f"/pictures/{post['image']}"
    return f"""        <nav class="breadcrumbs" aria-label="ניווט משני">
            <div class="container">
                <ol>
                    <li><a href="/">דף הבית</a></li>
                    <li><a href="/blog/">בלוג</a></li>
                    <li>{post["title"]}</li>
                </ol>
            </div>
        </nav>

        <section class="blog-post-hero" style="background-image: linear-gradient(rgba(0,0,0,0.55), rgba(0,0,0,0.55)), url('{img}');">
            <div class="container">
                <span class="blog-category-badge">{post["category"]}</span>
                <h1>{post["title"]}</h1>
                <div class="blog-post-meta">
                    <span><i class="far fa-calendar" aria-hidden="true"></i> {post["date_display"]}</span>
                    <span><i class="far fa-clock" aria-hidden="true"></i> {post["read_time"]}</span>
                </div>
            </div>
        </section>

        <section class="section-padding">
            <div class="container blog-article-layout">
                <article class="article-body">
                    <p class="article-lead">{post["excerpt"]}</p>
{sections}
{faq}
{sources}
{CTA_BOX}
                </article>

                <aside class="blog-sidebar">
                    <div class="sidebar-box">
                        <h4>שירותים רלוונטיים</h4>
                        <ul class="sidebar-links">
{related}
                            <li><a href="/services/">כל שירותי הגידור</a></li>
                        </ul>
                    </div>
{posts_box}{city_box}                    <div class="sidebar-box sidebar-contact">
                        <h4>שיחת ייעוץ חינם</h4>
                        <p><i class="fas fa-phone" aria-hidden="true"></i> <a href="tel:0507575570">050-757-5570</a></p>
                        <p><i class="fas fa-envelope" aria-hidden="true"></i> <a href="mailto:m0507575570@gmail.com">m0507575570@gmail.com</a></p>
                    </div>
                    <div class="sidebar-box">
                        <a href="/blog/" class="btn btn-secondary-dark btn-block"><i class="fas fa-arrow-right" aria-hidden="true"></i> חזרה לכל המאמרים</a>
                    </div>
                </aside>
            </div>
        </section>"""


def _build_index_content(posts):
    cards = []
    for post in posts:
        img = f"/pictures/{post['image']}"
        cards.append(f"""                <article class="blog-card">
                    <a href="/blog/{post['slug']}" class="blog-card-link">
                        <div class="blog-card-image"><img src="{img}" alt="{post['image_alt']}" title="{post['image_alt']}" loading="lazy"></div>
                        <div class="blog-card-body">
                            <span class="blog-category-badge">{post['category']}</span>
                            <h2 class="blog-card-title">{post['title']}</h2>
                            <p class="blog-card-excerpt">{post['excerpt']}</p>
                            <span class="blog-card-meta"><i class="far fa-calendar" aria-hidden="true"></i> {post['date_display']} · {post['read_time']}</span>
                        </div>
                    </a>
                </article>""")
    cards_html = "\n".join(cards)
    helpful = _render_link_list([
        {"url": "/services/", "label": "כל שירותי הגידור לאתרי בנייה",
         "note": "איסכורית, פאנל, רשת, שערים, מעברים, מיתוג ושילוט"},
        {"url": "/service-areas/", "label": "אזורי השירות שלנו בכל הארץ",
         "note": "רשימת היישובים שבהם אנחנו פועלים"},
        {"url": "/services/iskurit", "label": "גידור איסכורית",
         "note": "הפתרון הנפוץ ביותר לתיחום אטום של אתר בנייה"},
        {"url": "/services/temporary-fencing", "label": "גידור זמני והשכרת גדרות",
         "note": "אספקה, התקנה ופירוק לכל תקופת הפרויקט"},
    ], indent=16)
    return f"""        <section class="blog-index-hero">
            <div class="container">
                <h1>הבלוג של מרדכי סיונוב גידור</h1>
                <p>מדריכים, טיפים ומידע מקצועי על גידור אתרי בנייה — סוגי גדרות, בטיחות, תקנים ותכנון נכון של הפרויקט.</p>
            </div>
        </section>

        <section class="section-padding bg-light">
            <div class="container">
                <div class="blog-grid">
{cards_html}
                </div>
            </div>
        </section>

        <section class="section-padding">
            <div class="container">
                <h2 class="section-title">קישורים שימושיים</h2>
                <p>קראתם את המדריכים ואתם מוכנים להתקדם? אלה העמודים שיעזרו לכם לבחור את סוג הגדר
                    ולבדוק שאנחנו פועלים גם באזור הפרויקט שלכם:</p>
{helpful}
            </div>
        </section>"""


def build_blog():
    posts = read_json("data_blog.json")
    posts = sorted(posts, key=lambda p: p["date"], reverse=True)
    cities = read_json("data.json")
    template = Path("template_blog.html").read_text(encoding="utf-8")
    output_dir = Path("blog")
    output_dir.mkdir(exist_ok=True)

    # Individual posts
    for index, post in enumerate(posts):
        url = f"{SITE}/blog/{post['slug']}"
        page = template
        page = page.replace("{meta_title}", post["meta_title"])
        page = page.replace("{meta_description}", post["meta_description"])
        page = page.replace("{meta_keywords}", post["meta_keywords"])
        page = page.replace("{canonical}", url)
        page = page.replace("{hero_preload}", _hero_preload(f"/pictures/{post['image']}"))
        page = page.replace("{schema}", _post_schema(post, url))
        page = page.replace("{content}", _build_post_content(post, posts, cities, index))
        write_file(output_dir / f"{post['slug']}.html", page)
        print(f"Created blog post: blog/{post['slug']}.html")

    # Index
    index_schema = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": "הבלוג של מרדכי סיונוב גידור אתרי בניה",
        "url": f"{SITE}/blog/",
    }
    import json as _json
    schema_html = ('    <script type="application/ld+json">\n    '
                   + _json.dumps(index_schema, ensure_ascii=False, indent=4).replace("\n", "\n    ")
                   + "\n    </script>")
    page = template
    page = page.replace("{meta_title}", "בלוג גידור אתרי בנייה — מדריכים וטיפים | מרדכי סיונוב")
    page = page.replace("{meta_description}", "הבלוג של מרדכי סיונוב גידור אתרי בניה: מדריכים על סוגי גדרות, מחירים, בטיחות ותקנים בגידור אתרי בנייה. ידע מקצועי מהשטח.")
    page = page.replace("{meta_keywords}", "בלוג גידור, גידור אתרי בניה, גדר איסכורית, מחיר גידור, תקנים בטיחות")
    page = page.replace("{canonical}", f"{SITE}/blog/")
    page = page.replace("{hero_preload}", "")
    page = page.replace("{schema}", schema_html)
    page = page.replace("{content}", _build_index_content(posts))
    write_file(output_dir / "index.html", page)
    print("Created blog index: blog/index.html")


if __name__ == "__main__":
    build_city_pages()
    build_service_pages()
    build_blog()
    print("Done! All pages created successfully.")
