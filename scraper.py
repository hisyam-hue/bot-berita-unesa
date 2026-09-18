import pandas as pd
import re
import time
from playwright.sync_api import sync_playwright

CSV_FILE = "rekap_berita_unesa.csv"
MAX_PAGES = 5  # Mengambil 5 halaman (sekitar 50 berita September)

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

def run_scraper():
    all_articles = []
    seen_links = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Membuka halaman berita Unesa...")
        page.goto("https://www.unesa.ac.id/page/berita", timeout=60000)

        for p_num in range(1, MAX_PAGES + 1):
            print(f"Mengambil data halaman {p_num}...")
            time.sleep(3)  # Tunggu AJAX render

            # Ambil HTML konten
            html = page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            a_tags = soup.find_all('a', href=re.compile(r'/read/'))
            count = 0
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
                count += 1

            print(f"Halaman {p_num}: didapat {count} berita.")

            # Klik tombol Next/Halaman berikutnya
            if p_num < MAX_PAGES:
                try:
                    next_button = page.locator(f"a:has-text('{p_num + 1}')").first
                    if next_button.is_visible():
                        next_button.click()
                    else:
                        break
                except Exception as e:
                    print(f"Gagal pindah ke halaman {p_num + 1}: {e}")
                    break

        browser.close()

    if all_articles:
        df = pd.DataFrame(all_articles)
        df.to_csv(CSV_FILE, index=False)
        print(f"Selesai! Berhasil merekap {len(df)} berita.")

if __name__ == "__main__":
    run_scraper()
