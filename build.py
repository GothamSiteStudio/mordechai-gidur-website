import json
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


# ---------- City pages ----------
def build_city_pages():
    pages = read_json("data.json")
    template = Path("template_city.html").read_text(encoding="utf-8")
    output_dir = Path("service-areas")
    output_dir.mkdir(exist_ok=True)

    for page in pages:
        canonical = f"{SITE}/service-areas/{page['filename'][:-5]}"
        new_content = template
        new_content = new_content.replace("{canonical}", canonical)
        new_content = new_content.replace("{city_name}", page["city_name"])
        new_content = new_content.replace("{region}", page["region"])
        new_content = new_content.replace("{seo_desc_start}", page["seo_desc_start"])
        new_content = new_content.replace("{unique_paragraph_1}", page["unique_paragraph_1"])
        new_content = new_content.replace("{unique_paragraph_2}", page["unique_paragraph_2"])

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
    return "\n".join(f'{pad}<li><i class="fas fa-check"></i> {text}</li>' for text in items)


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
{card_pad}<i class="{rel["icon"]}"></i>
{card_pad}<h4>{rel["title"]}</h4>
{pad}</a>"""
        )
    return "\n".join(cards)


def build_service_pages():
    services = read_json("data_services.json")
    template = Path("template_service.html").read_text(encoding="utf-8")
    output_dir = Path("services")
    output_dir.mkdir(exist_ok=True)

    primary_menu = [s for s in services if s.get("menu_group") == "primary"]
    secondary_menu = [s for s in services if s.get("menu_group") != "primary"]
    footer_services = services[:6]

    for svc in services:
        menu_primary_links = _render_links(primary_menu, indent=32)
        menu_secondary_links = _render_links(secondary_menu, indent=32)
        benefits_list = _render_benefits(svc["benefits"], indent=24)
        uses_list = _render_list(svc["uses"], indent=24)
        spec_rows = _render_specs(svc["specs"], indent=28)
        sidebar_links = _render_links(services, indent=28, exclude=svc["filename"])
        footer_service_links = _render_links(footer_services, indent=24)
        related_cards = _render_related(svc["related"], indent=20)

        replacements = {
            "{meta_title}": svc["meta_title"],
            "{meta_description}": svc["meta_description"],
            "{meta_keywords}": svc["meta_keywords"],
            "{canonical}": svc["canonical"],
            "{service_name}": svc["service_name"],
            "{schema_description}": svc["schema_description"],
            "{hero_title}": svc["hero_title"],
            "{hero_subtitle}": svc["hero_subtitle"],
            "{intro_heading}": svc["intro_heading"],
            "{intro_paragraph}": svc["intro_paragraph"],
            "{benefits_heading}": svc["benefits_heading"],
            "{benefits_list}": benefits_list,
            "{uses_heading}": svc["uses_heading"],
            "{uses_intro}": svc["uses_intro"],
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
                html.append(f'                        <li><i class="fas fa-check"></i> {it}</li>')
            html.append('                    </ul>')
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
        "dateModified": post["date"],
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
                            <a href="tel:0507575570" class="btn btn-primary"><i class="fas fa-phone-alt"></i> 050-757-5570</a>
                            <a href="https://wa.me/972507575570" class="btn btn-secondary-dark" target="_blank"><i class="fab fa-whatsapp"></i> וואטסאפ</a>
                        </div>
                    </div>"""


def _build_post_content(post):
    sections = _render_article_sections(post["sections"])
    faq = _render_faq(post.get("faq"))
    related = _render_related_sidebar(post["related_services"])
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
                    <span><i class="far fa-calendar"></i> {post["date_display"]}</span>
                    <span><i class="far fa-clock"></i> {post["read_time"]}</span>
                </div>
            </div>
        </section>

        <section class="section-padding">
            <div class="container blog-article-layout">
                <article class="article-body">
                    <p class="article-lead">{post["excerpt"]}</p>
{sections}
{faq}
{CTA_BOX}
                </article>

                <aside class="blog-sidebar">
                    <div class="sidebar-box">
                        <h4>שירותים רלוונטיים</h4>
                        <ul class="sidebar-links">
{related}
                        </ul>
                    </div>
                    <div class="sidebar-box sidebar-contact">
                        <h4>שיחת ייעוץ חינם</h4>
                        <p><i class="fas fa-phone"></i> <a href="tel:0507575570">050-757-5570</a></p>
                        <p><i class="fas fa-envelope"></i> <a href="mailto:m0507575570@gmail.com">m0507575570@gmail.com</a></p>
                    </div>
                    <div class="sidebar-box">
                        <a href="/blog/" class="btn btn-secondary-dark btn-block"><i class="fas fa-arrow-right"></i> חזרה לכל המאמרים</a>
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
                        <div class="blog-card-image"><img src="{img}" alt="{post['image_alt']}" loading="lazy"></div>
                        <div class="blog-card-body">
                            <span class="blog-category-badge">{post['category']}</span>
                            <h2 class="blog-card-title">{post['title']}</h2>
                            <p class="blog-card-excerpt">{post['excerpt']}</p>
                            <span class="blog-card-meta"><i class="far fa-calendar"></i> {post['date_display']} · {post['read_time']}</span>
                        </div>
                    </a>
                </article>""")
    cards_html = "\n".join(cards)
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
        </section>"""


def build_blog():
    posts = read_json("data_blog.json")
    posts = sorted(posts, key=lambda p: p["date"], reverse=True)
    template = Path("template_blog.html").read_text(encoding="utf-8")
    output_dir = Path("blog")
    output_dir.mkdir(exist_ok=True)

    # Individual posts
    for post in posts:
        url = f"{SITE}/blog/{post['slug']}"
        page = template
        page = page.replace("{meta_title}", post["meta_title"])
        page = page.replace("{meta_description}", post["meta_description"])
        page = page.replace("{meta_keywords}", post["meta_keywords"])
        page = page.replace("{canonical}", url)
        page = page.replace("{schema}", _post_schema(post, url))
        page = page.replace("{content}", _build_post_content(post))
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
    page = page.replace("{schema}", schema_html)
    page = page.replace("{content}", _build_index_content(posts))
    write_file(output_dir / "index.html", page)
    print("Created blog index: blog/index.html")


if __name__ == "__main__":
    build_city_pages()
    build_service_pages()
    build_blog()
    print("Done! All pages created successfully.")
