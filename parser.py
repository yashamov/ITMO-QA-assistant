# parser.py

import requests
from bs4 import BeautifulSoup
import re

PROGRAM_URLS = {
    "ai": "https://abit.itmo.ru/program/master/ai",
    "ai_product": "https://abit.itmo.ru/program/master/ai_product",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; itmo-gpt-bot/1.0)"
}

def parse_program(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Название программы
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Институт
    institute_tag = soup.find("a", href=lambda h: h and "viewfaculty" in h)
    institute = institute_tag.get_text(strip=True) if institute_tag else None

    # Ключевые характеристики (форма, длительность, стоимость, язык, общежитие)
    meta = {}
    for card in soup.select(".Information_card__rshys"):
        label = card.select_one(".Information_card__header__6PpVf p")
        value = card.select_one(".Information_card__text__txwcx")
        if label and value:
            meta[label.text.strip().lower()] = value.text.strip()

    # О программе
    about = extract_section(soup, "о программе")

    # Карьера
    career = extract_section(soup, "карьера")

    # Как поступить
    admission = extract_section(soup, "как поступить")

    # FAQ (часто задаваемые вопросы)
    faq = extract_faq(soup)

    # Ссылка на PDF учебного плана
    pdf_link = None
    for a in soup.find_all("a", href=True):
        if "pdf" in a["href"].lower() or "учебный план" in a.text.lower():
            pdf_link = a["href"]
            break

    return {
        "title": title,
        "institute": institute,
        "meta": meta,
        "about": about,
        "career": career,
        "admission": admission,
        "faq": faq,
        "curriculum_pdf_url": pdf_link,
        "url": url,
    }

def extract_section(soup, section_name):
    block = soup.find("h2", string=lambda t: t and section_name in t.lower())
    section = ""
    if block:
        for sib in block.find_next_siblings():
            if sib.name and sib.name.startswith("h2"):
                break
            section += sib.get_text(" ", strip=True) + " "
    return section.strip()

def extract_faq(soup):
    faq = {}
    for h in soup.find_all("h3"):
        q = h.get_text(strip=True)
        if "?" in q:
            a_elem = []
            for sib in h.find_next_siblings():
                if sib.name and sib.name.startswith("h3"):
                    break
                a_elem.append(sib.get_text(" ", strip=True))
            faq[q] = " ".join(filter(None, a_elem)).strip()
    return faq or None

def fetch_all_programs():
    return {slug: parse_program(url) for slug, url in PROGRAM_URLS.items()}


'''
if __name__ == "__main__":
    programs = fetch_all_programs()
    import json
    for slug, data in programs.items():
        print(f"\n=== {data['title']} ===")
        print(json.dumps(data, ensure_ascii=False, indent=2))
'''