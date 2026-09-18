import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }

    all_articles = []
    seen_links = set()

    # 1. Coba Tarik via API JSON Internal Unesa
    api_success = False
    for page in range(1, 15):
        api_url = f"https://www.unesa.ac.id/api/berita?page={page}"
        try:
            res = requests.get(api_url, headers=headers, timeout=10)
            if res.status_code == 200 and 'json' in res.headers.get('Content-Type', ''):
                data = res.json()
                items = data.get('data', []) or data.get('posts', []) or data
                if isinstance(items, list) and len(items) > 0:
                    api_success = True
                    for item in items:
                        judul = clean_text(item.get('title', '') or item.get('judul', ''))
                        link = item.get('url', '') or item.get('link', '')
                        date_str = item.get('created_at', '') or item.get('tanggal', '')
                        kategori = item.get('category', '') or "Berita Utama"

                        if link and link not in seen_links and len(judul) > 5:
                            day, month, year, formatted_date = parse_date(date_str)
                            all_articles.append({
                                'tanggal': formatted_date,
                                'judul': judul,
                                'kategori': kategori,
                                'link': link,
                                'bulan': month,
                                'tahun': year
                            })
                            seen_links.add(link)
        except Exception:
            pass

    # 2. Jika API internal dikunci, lakukan scraping dari berbagai jalur direktori kanal Unesa
    if not api_success or len(all_articles) < 20:
        base_channels = [
            "https://www.unesa.ac.id/page/berita",
            "https://www.unesa.ac.id/page/berita/1",
            "https://www.unesa.ac.id/page/berita/2",
            "https://www.unesa.ac.id/page/berita/3",
            "https://www.unesa.ac.id/page/berita/4",
            "https://www.unesa.ac.id/category/berita-utama",
            "https://www.unesa.ac.id/category/unesacategory"
        ]

        for target_url in base_channels:
            try:
                res = requests.get(target_url, headers=headers, timeout=12)
                if res.status_code != 200:
                    continue

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

                        cat_elem = parent.find(class_=re.compile(r'cat|kategori|badge|tag', re.I))
                        if cat_elem:
                            kategori = clean_text(cat_elem.get_text())

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
                print(f"Error pada {target_url}: {e}")

    if all_articles:
        final_df = pd.DataFrame(all_articles)
        final_df.to_csv(CSV_FILE, index=False)
        print(f"Berhasil merekap total {len(final_df)} artikel ke {CSV_FILE}.")
    else:
        print("Gagal mengambil data.")

if __name__ == "__main__":
    scrape_unesa()
