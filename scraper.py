import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import xml.etree.ElementTree as ET

CSV_FILE = "rekap_berita_unesa.csv"

MONTH_MAP = {
    'Januari': 1, 'Jan': 1, 'Februari': 2, 'Feb': 2, 'Maret': 3, 'Mar': 3,
    'April': 4, 'Apr': 4, 'Mei': 5, 'Juni': 6, 'Jun': 6, 'Juli': 7, 'Jul': 7,
    'Agustus': 8, 'Agu': 8, 'Ags': 8, 'September': 9, 'Sep': 9,
    'Oktober': 10, 'Okt': 10, 'November': 11, 'Nov': 11, 'Desember': 12, 'Des': 12
}

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_date(date_str):
    date_str = clean_text(date_str)
    match = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', date_str)
    if match:
        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))
        month = MONTH_MAP.get(month_name, None)
        return day, month, year, f"{day} {month_name} {year}"
    return None, None, None, date_str

def scrape_unesa():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    }

    all_articles = []
    seen_links = set()

    # Target URL: RSS Feed & Arsip Tanggal September 2026
    target_urls = [
        "https://www.unesa.ac.id/feed",
        "https://www.unesa.ac.id/page/berita/feed",
        "https://www.unesa.ac.id/2026/09/",
        "https://www.unesa.ac.id/page/berita"
    ]

    for url in target_urls:
        print(f"Mencoba ekstraksi dari: {url}")
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200:
                continue

            # Jika respon berbentuk XML / RSS Feed
            if 'xml' in res.headers.get('Content-Type', '') or url.endswith('/feed'):
                try:
                    root = ET.fromstring(res.content)
                    for item in root.findall('.//item'):
                        title = clean_text(item.find('title').text if item.find('title') is not None else "")
                        link = clean_text(item.find('link').text if item.find('link') is not None else "")
                        pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                        
                        if link and link not in seen_links and len(title) > 10:
                            day, month, year, formatted_date = parse_date(pub_date)
                            all_articles.append({
                                'tanggal': formatted_date,
                                'judul': title,
                                'kategori': "Berita Utama",
                                'link': link,
                                'bulan': month or 9,
                                'tahun': year or 2026
                            })
                            seen_links.add(link)
                except Exception as e_xml:
                    print(f"Parsing RSS XML gagal, lanjut metode HTML parsing: {e_xml}")

            # Metode HTML Parsing
            soup = BeautifulSoup(res.text, 'html.parser')
            a_tags = soup.find_all('a', href=re.compile(r'/read/'))

            for a in a_tags:
                link = a.get('href', '')
                if not link.startswith('http'):
                    link = 'https://www.unesa.ac.id' + link

                if link in seen_links:
                    continue

                judul = clean_text(a.get_text())
                parent = a.find_parent(['div', 'article', 'li'])
                
                if len(judul) < 15 or "Read More" in judul:
                    if parent:
                        h_tag = parent.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                        if h_tag:
                            judul = clean_text(h_tag.get_text())

                if not judul or len(judul) < 10 or "Read More" in judul:
                    continue

                date_text = ""
                kategori = "Berita Umum"
                if parent:
                    text_all = parent.get_text()
                    dm = re.search(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}', text_all)
                    if dm:
                        date_text = dm.group(0)

                day, month, year, formatted_date = parse_date(date_text)

                all_articles.append({
                    'tanggal': formatted_date,
                    'judul': judul,
                    'kategori': kategori,
                    'link': link,
                    'bulan': month,
                    'tahun': year
                })
                seen_links.add(link)

        except Exception as e:
            print(f"Error pada {url}: {e}")

    if all_articles:
        final_df = pd.DataFrame(all_articles)
        final_df.to_csv(CSV_FILE, index=False)
        print(f"Selesai! Berhasil merekap {len(final_df)} berita.")
    else:
        print("Gagal mengambil data.")

if __name__ == "__main__":
    scrape_unesa()
