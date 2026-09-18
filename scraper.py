import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

BASE_URL = "https://www.unesa.ac.id/page/berita"
CSV_FILE = "rekap_berita_unesa.csv"
MAX_PAGES = 25  # Menyapu penuh 25 halaman berita

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    all_articles = []
    seen_links = set()

    for page in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}?page={page}" if page > 1 else BASE_URL
        print(f"Scraping halaman {page}: {url}")

        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200:
                print(f"Gagal memuat halaman {page}")
                break

            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Cari elemen artikel berita
            articles = soup.find_all(['div', 'article'], class_=re.compile(r'post|news|berita|card|item|col', re.I))

            for art in articles:
                a_tag = art.find('a', href=re.compile(r'/read/'))
                if not a_tag:
                    continue

                link = a_tag.get('href', '')
                if not link.startswith('http'):
                    link = 'https://www.unesa.ac.id' + link

                if link in seen_links:
                    continue

                h_tag = art.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                judul = clean_text(h_tag.get_text()) if h_tag else clean_text(a_tag.get_text())

                if not judul or len(judul) < 10 or "Read More" in judul:
                    continue

                date_text = ""
                date_elem = art.find(text=re.compile(r'\d{4}'))
                if date_elem:
                    date_text = str(date_elem).strip()

                cat_elem = art.find(class_=re.compile(r'cat|kategori|badge|label|tag', re.I))
                kategori = clean_text(cat_elem.get_text()) if cat_elem else "Berita Umum"

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
            print(f"Error halaman {page}: {e}")
            break

    if all_articles:
        final_df = pd.DataFrame(all_articles)
        final_df.to_csv(CSV_FILE, index=False)
        print(f"Berhasil! Rekap total {len(final_df)} berita disimpan ke {CSV_FILE}.")
    else:
        print("Tidak ada artikel yang diambil.")

if __name__ == "__main__":
    scrape_unesa()
