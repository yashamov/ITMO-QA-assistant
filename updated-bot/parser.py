import requests
from bs4 import BeautifulSoup
import pdfplumber
import io
import re

PROGRAM_URLS = {
    "ai": "https://abit.itmo.ru/program/master/ai",
    "ai_product": "https://abit.itmo.ru/program/master/ai_product",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; itmo-gpt-bot/1.0)"
}

def fetch_program_html(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def find_curriculum_pdf_link(soup):
    # Самый надёжный способ — по структуре ссылки!
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True).lower()
        # Ищем только файл в curriculum и с pdf
        if (
            ".pdf" in href
            and "/file_storage/file/curriculum/" in href
            and "учеб" in text
        ):
            if href.startswith("/"):
                return "https://abit.itmo.ru" + href
            return href
    # Резервный способ — ищем <a> с кнопкой "Скачать учебный план"
    for a in soup.find_all("a", href=True):
        button = a.find("button")
        if button and "учебный план" in button.get_text(strip=True).lower():
            href = a["href"]
            if href.startswith("/"):
                return "https://abit.itmo.ru" + href
            return href
    return None

def parse_pdf_curriculum(pdf_url):
    pdf_bytes = requests.get(pdf_url, timeout=30).content
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        disciplines = []
        current_type = None
        block_types = [
            ("обязательные дисциплины", "Обязательные дисциплины"),
            ("пул выборных дисциплин", "Элективные дисциплины"),
            ("универсальная", "Универсальная подготовка"),
            ("факультатив", "Факультатив"),
            ("микромодули", "Элективные микромодули"),
        ]
        for page in pdf.pages:
            lines = page.extract_text().split('\n')
            for line in lines:
                line = line.strip()
                line_low = line.lower()
                for marker, rusname in block_types:
                    if marker in line_low:
                        current_type = rusname
                        break
                # Парсим строку вида: "1 Воркшоп ... 3 108"
                m = re.match(r"^(\d+(?:,\s*\d+)*)\s+(.+?)\s+(\d{1,2})\s+(\d{2,4})$", line)
                if m:
                    semester, title, credits, hours = m.groups()
                    disciplines.append({
                        "semester": semester,
                        "title": title.strip(),
                        "credits": int(credits),
                        "hours": int(hours),
                        "type": current_type
                    })
        return disciplines

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


PDF_URLS = {
    "ai": "https://api.itmo.su/constructor-ep/api/v1/static/programs/10033/plan/abit/pdf",
    "ai_product": "https://api.itmo.su/constructor-ep/api/v1/static/programs/10130/plan/abit/pdf",
}

def parse_program(url, slug):
    soup = fetch_program_html(url)
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""
    institute_tag = soup.find("a", href=lambda h: h and "viewfaculty" in h)
    institute = institute_tag.get_text(strip=True) if institute_tag else None

    meta = {}
    for card in soup.select(".Information_card__rshys"):
        label = card.select_one(".Information_card__header__6PpVf p")
        value = card.select_one(".Information_card__text__txwcx")
        if label and value:
            meta[label.text.strip().lower()] = value.text.strip()
    about = extract_section(soup, "о программе")
    career = extract_section(soup, "карьера")
    admission = extract_section(soup, "как поступить")
    faq = extract_faq(soup)

    # Теперь получаем ссылку на учебный план из PDF_URLS
    pdf_link = PDF_URLS.get(slug)
    curriculum_disciplines = []
    if pdf_link:
        try:
            curriculum_disciplines = parse_pdf_curriculum(pdf_link)
        except Exception as e:
            print(f"Ошибка при парсинге PDF для {title}: {e}")
    else:
        print(f"PDF учебного плана не найден для {url}")

    return {
        "title": title,
        "institute": institute,
        "meta": meta,
        "about": about,
        "career": career,
        "admission": admission,
        "faq": faq,
        "curriculum_pdf_url": pdf_link,
        "curriculum_disciplines": curriculum_disciplines,
        "url": url,
    }

def fetch_all_programs():
    return {slug: parse_program(url, slug) for slug, url in PROGRAM_URLS.items()}

