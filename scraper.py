import pandas as pd
import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

CSV_FILE = "rekap_berita_unesa.csv"
MAX_PAGES = 5  # Menyapu 5 halaman (sekitar 50 berita September)

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
        # Launch browser chromium headless
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        print("Membuka halaman berita UNESA...")
        try:
            page.goto("https://www.unesa.ac.id/page/berita", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"Gagal membuka halaman awal: {e}")

        for p_num in range(1, MAX_PAGES + 1):
            print(f"=== Mengambil data halaman {p_num} ===")
            page.wait_for_timeout(3000)  # Tunggu render AJAX

            html = page.content()
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

                if len(judul) < 15 or "Read More" in judul or "Selengkapnya" in judul:
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
                count += 1

            print(f"Halaman {p_num}: didapat {count} berita baru.")

            # Berpindah ke halaman berikutnya
            if p_num < MAX_PAGES:
                clicked = False
                # Coba beberapa variasi penulisan tombol pagination
                targets = [
                    f"text='{p_num + 1}'",
                    f"a:has-text('{p_num + 1}')",
                    ".pagination li a:has-text('Next')",
                    ".page-link:has-text('»')"
                ]
                for target in targets:
                    try:
                        elem = page.locator(target).first
                        if elem.is_visible():
                            elem.click()
                            clicked = True
                            print(f"Berhasil mengklik halaman {p_num + 1} menggunakan target: {target}")
                            break
                    except Exception:
                        continue

                if not clicked:
                    print(f"Tidak dapat menemukan tombol navigasi ke halaman {p_num + 1}. Menghentikan perulangan.")
                    break

        browser.close()

    if all_articles:
        df = pd.DataFrame(all_articles)
        df.to_csv(CSV_FILE, index=False)
        print(f"Selesai! Total {len(df)} artikel berhasil disave ke {CSV_FILE}.")
    else:
        print("Tidak ada artikel yang berhasil diekstrak.")

if __name__ == "__main__":
    run_scraper()
