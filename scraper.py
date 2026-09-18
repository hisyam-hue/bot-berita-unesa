import os
import re
import time
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Map bulan Indonesia ke angka
bulan_map = {
    "januari": 1, "jan": 1,
    "februari": 2, "feb": 2,
    "maret": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mei": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "agustus": 8, "agu": 8, "aug": 8,
    "september": 9, "sep": 9,
    "oktober": 10, "okt": 10, "oct": 10,
    "november": 11, "nov": 11,
    "desember": 12, "des": 12, "dec": 12
}

def klasifikasi_tema(judul):
    txt = judul.lower()
    if any(k in txt for k in ["juara", "medali", "penghargaan", "gemilang", "peringkat", "prestasi", "borong"]):
        return "Prestasi Institusi"
    elif any(k in txt for k in ["mahasiswa", "ormawa", "ukm", "pembinaan", "kegiatan mahasiswa", "tep"]):
        return "Kemahasiswaan"
    elif any(k in txt for k in ["delegasi", "kerja sama", "kerjasama", "kunjungan", "mou", "kemitraan", "australia"]):
        return "Kerjasama"
    elif any(k in txt for k in ["inovasi", "riset", "penelitian", "pakar", "sastra", "stroke", "buku", "kajian"]):
        return "Inovasi & Penelitian"
    elif any(k in txt for k in ["masyarakat", "pengabdian", "desa", "pendampingan", "bakti"]):
        return "Pengabdian Masyarakat"
    else:
        return "Berita Umum"

def parse_art_info(art):
    text = art.get_text(separator=" ")
    match_date = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text, re.IGNORECASE)
    tgl_str, bln_num, thn_num = datetime.now().strftime("%d %b %Y"), datetime.now().month, 2026

    if match_date:
        day = match_date.group(1)
        month_name = match_date.group(2).lower()
        year = int(match_date.group(3))
        if month_name in bulan_map:
            bln_num = bulan_map[month_name]
            thn_num = year
            tgl_str = f"{day} {match_date.group(2).capitalize()} {year}"

    return tgl_str, bln_num, thn_num

def run_scraper():
    print("Menjalankan Auto Scraper Unesa di Cloud (Full Scan 2026)...")
    news_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    stop_scraping = False
    # Pindai hingga 25 halaman agar seluruh berita September 2026 (40+ berita) terekap sempurna
    for page in range(1, 26):
        if stop_scraping:
            break

        url = (
            "https://unesa.ac.id/category/berita-unesa"
            if page == 1
            else f"https://unesa.ac.id/category/berita-unesa/p/{page}/"
        )
        print(f"Scraping Halaman {page}: {url}")

        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                print(f"Halaman {page} tidak merespons (Status {res.status_code}). Selesai.")
                break

            soup = BeautifulSoup(res.text, "html.parser")
            articles = soup.find_all("article")
            if not articles:
                articles = soup.select(".post, .entry, .item, .card")

            if not articles:
                print(f"Tidak ada artikel ditemukan pada Halaman {page}.")
                break

            for art in articles:
                title_tag = art.find("h2") or art.find("h3") or art.find("h4")
                if not title_tag:
                    continue

                a_tag = title_tag.find("a", href=True) or art.find("a", href=True)
                if not a_tag:
                    continue

                title = a_tag.text.strip()
                link = a_tag["href"]

                if (
                    len(title) > 12
                    and not link.startswith("#")
                    and "category" not in link
                ):
                    full_link = (
                        link
                        if link.startswith("http")
                        else f"https://unesa.ac.id{link}"
                    )
                    tgl, bln, thn = parse_art_info(art)

                    # Hentikan jika mendeteksi berita tahun 2025 atau sebelumnya
                    if thn < 2026:
                        stop_scraping = True
                        break

                    kategori_tema = klasifikasi_tema(title)

                    news_list.append(
                        {
                            "tanggal": tgl,
                            "judul": title,
                            "kategori": kategori_tema,
                            "link": full_link,
                            "bulan": bln,
                            "tahun": thn,
                        }
                    )
            time.sleep(0.3)
        except Exception as e:
            print(f"Error halaman {page}: {e}")
            break

    if news_list:
        df_new = pd.DataFrame(news_list).drop_duplicates(subset=["link"])
        file_name = "rekap_berita_unesa.csv"

        if os.path.exists(file_name):
            df_old = pd.read_csv(file_name)
            df_combined = (
                pd.concat([df_new, df_old])
                .drop_duplicates(subset=["link"], keep="first")
                .reset_index(drop=True)
            )
            df_combined.to_csv(file_name, index=False)
            print(f"BERHASIL! Total {len(df_combined)} berita tersimpan di {file_name}")
        else:
            df_new.to_csv(file_name, index=False)
            print(f"BERHASIL! Total {len(df_new)} berita tersimpan di {file_name}")
    else:
        print("Tidak ada berita baru yang ditarik.")

if __name__ == "__main__":
    run_scraper()
