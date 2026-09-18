import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os

BASE_URL = "https://www.unesa.ac.id/page/berita"
CSV_FILE = "rekap_berita_unesa.csv"
MAX_PAGES = 25

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

    for page in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}?page={page}" if page > 1 else BASE_URL
        print(f"Scraping halaman {page}: {url}")

        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code != 200:
                print(f"Gagal akses halaman {page}")
                break

            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Cari seluruh elemen tautan yang menuju artikel berita /read/
            all_a_tags = soup.find_all('a', href=re.compile(r'/read/'))

            count_page = 0
            for a in all_a_tags:
                link = a.get('href', '')
                if not link.startswith('http'):
                    link = 'https://www.unesa.ac.id' + link

                if link in seen_links:
                    continue

                # Ambil judul artikel dari tag <a> atau parent terdekat
                judul = clean_text(a.get_text())
                if len(judul) < 15 or "Read More" in judul or "Selengkapnya" in judul:
                    parent = a.find_parent(['div', 'article', 'li', 'td'])
                    if parent:
                        h_tag = parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                        if h_tag:
                            judul = clean_text(h_tag.get_text())

                if not judul or len(judul) < 10 or "Read More" in judul:
                    continue

                # Cari informasi tanggal & kategori dari blok kontainer terdekat
                parent = a.find_parent(['div', 'article', 'li'])
                date_text = ""
                kategori = "Berita Umum"

                if parent:
                    # Ambil teks tanggal
                    text_content = parent.get_text()
                    date_match = re.search(r'\d{1,2}\s+[A-Za-z]+\s+\d{4}', text_content)
                    if date_match:
                        date_text = date_match.group(0)

                    # Ambil kategori jika ada
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

            print(f"Halaman {page}: didapat {count_page} berita baru.")
            if count_page == 0 and page > 1:
                print("Tidak ada berita tambahan, menghentikan ekstraksi.")
                break

        except Exception as e:
            print(f"Error pada halaman {page}: {e}")
            break

    if all_articles:
        final_df = pd.DataFrame(all_articles)
        final_df.to_csv(CSV_FILE, index=False)
        print(f"Selesai! Berhasil menyimpan total {len(final_df)} artikel ke {CSV_FILE}.")
    else:
        print("Tidak ada artikel yang diambil.")

if __name__ == "__main__":
    scrape_unesa()
