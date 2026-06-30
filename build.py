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


if __name__ == "__main__":
    build_city_pages()
    build_service_pages()
    print("Done! All pages created successfully.")
