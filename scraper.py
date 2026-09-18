import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os

BASE_URL = "https://www.unesa.ac.id/page/berita"
CSV_FILE = "rekap_berita_unesa.csv"
MAX_PAGES = 25  # Menjangkau 25 halaman untuk menyapu seluruh berita 2026

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
                print(f"Gagal memuat halaman {page}, status: {res.status_code}")
                break

            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Cari semua tautan/link yang mengarah ke artikel berita (/read/...)
            links = soup.find_all('a', href=re.compile(r'/read/'))

            if not links:
                print(f"Tidak ada link berita di halaman {page}")
                break

            count_page = 0
            for a in links:
                link = a.get('href', '')
                if not link.startswith('http'):
                    link = 'https://www.unesa.ac.id' + link

                # Hindari duplikat link
                if link in seen_links:
                    continue

                # Ambil teks judul
                judul = clean_text(a.get_text())
                if len(judul) < 15 or "Read More" in judul or "Selengkapnya" in judul:
                    # Cari judul di parent element jika tag <a> tidak berisi judul lengkap
                    parent = a.find_parent(['div', 'article', 'li'])
                    if parent:
                        h_tag = parent.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                        if h_tag:
                            judul = clean_text(h_tag.get_text())

                if not judul or len(judul) < 10:
                    continue

                # Cari tanggal & kategori dari kontainer terdekat
                parent = a.find_parent(['div', 'article', 'li'])
                date_text = ""
                kategori = "Berita Umum"

                if parent:
                    # Tanggal
                    date_elem = parent.find(text=re.compile(r'\d{4}'))
                    if date_elem:
                        date_text = date_elem.strip()
                    
                    # Kategori
                    cat_elem = parent.find(class_=re.compile(r'cat|kategori|badge|label|tag', re.I))
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
                count_page += 1

            print(f"Halaman {page}: berhasil mengambil {count_page} artikel.")

        except Exception as e:
            print(f"Error pada halaman {page}: {e}")
            break

    if all_articles:
        final_df = pd.DataFrame(all_articles)
        final_df.to_csv(CSV_FILE, index=False)
        print(f"Selesai! Total {len(final_df)} artikel berhasil disimpan ke {CSV_FILE}.")
    else:
        print("Tidak ada artikel yang berhasil diambil.")

if __name__ == "__main__":
    scrape_unesa()
