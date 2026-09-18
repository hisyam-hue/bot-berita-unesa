import os
import re
import time
from datetime import datetime
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Map bulan
bulan_map = {
    "januari": 1,
    "jan": 1,
    "februari": 2,
    "feb": 2,
    "maret": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "mei": 5,
    "juni": 6,
    "jun": 6,
    "juli": 7,
    "jul": 7,
    "agustus": 8,
    "agu": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "oktober": 10,
    "okt": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "desember": 12,
    "des": 12,
    "dec": 12,
}


def klasifikasi_tema(judul):
    txt = judul.lower()
    if any(
        k in txt
        for k in [
            "juara",
            "medali",
            "penghargaan",
            "gemilang",
            "peringkat",
            "prestasi",
            "borong",
        ]
    ):
        return "Prestasi Institusi"
    elif any(
        k in txt
        for k in [
            "mahasiswa",
            "ormawa",
            "ukm",
            "pembinaan",
            "kegiatan mahasiswa",
            "tep",
        ]
    ):
        return "Kemahasiswaan"
    elif any(
        k in txt
        for k in [
            "delegasi",
            "kerja sama",
            "kerjasama",
            "kunjungan",
            "mou",
            "kemitraan",
            "australia",
        ]
    ):
        return "Kerjasama"
    elif any(
        k in txt
        for k in [
            "inovasi",
            "riset",
            "penelitian",
            "pakar",
            "sastra",
            "stroke",
            "buku",
            "kajian",
        ]
    ):
        return "Inovasi & Penelitian"
    elif any(
        k in txt
        for k in ["masyarakat", "pengabdian", "desa", "pendampingan", "bakti"]
    ):
        return "Pengabdian Masyarakat"
    else:
        return "Berita Umum"


def parse_art_info(art):
    text = art.get_text(separator=" ")
    match_date = re.search(
        r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text, re.IGNORECASE
    )
    tgl_str, bln_num, thn_num = (
        datetime.now().strftime("%d %b %Y"),
        datetime.now().month,
        2026,
    )

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
    print("Menjalankan Auto Scraper Unesa di Cloud...")
    news_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # Tarik berita terbaru dari 5 halaman pertama saja (untuk update harian)
    for page in range(1, 6):
        url = (
            "https://unesa.ac.id/category/berita-unesa"
            if page == 1
            else f"https://unesa.ac.id/category/berita-unesa/p/{page}/"
        )
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "html.parser")
            articles = soup.find_all("article")
            if not articles:
                articles = soup.select(".post, .entry, .item, .card")

            for art in articles:
                title_tag = art.find("h2") or art.find("h3") or art.find("h4")
                if not title_tag:
                    continue

                a_tag = title_tag.find("a", href=True) or art.find(
                    "a", href=True
                )
                if not a_tag:
                    continue

                title = a_tag.text.strip()
                link = a_tag["href"]

                if (
                    len(title) > 15
                    and not link.startswith("#")
                    and "category" not in link
                ):
                    full_link = (
                        link
                        if link.startswith("http")
                        else f"https://unesa.ac.id{link}"
                    )
                    tgl, bln, thn = parse_art_info(art)
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

    df_new = pd.DataFrame(news_list).drop_duplicates(subset=["link"])

    # Simpan/update CSV
    file_name = "rekap_berita_unesa.csv"
    if os.path.exists(file_name):
        df_old = pd.read_csv(file_name)
        df_combined = (
            pd.concat([df_new, df_old])
            .drop_duplicates(subset=["link"])
            .reset_index(drop=True)
        )
        df_combined.to_csv(file_name, index=False)
        print(f"Selesai! Data diperbarui. Total: {len(df_combined)} berita.")
    else:
        df_new.to_csv(file_name, index=False)
        print(f"Selesai! Data baru tersimpan. Total: {len(df_new)} berita.")


if __name__ == "__main__":
    run_scraper()
