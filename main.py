"""
main.py: Eksekusi Utama Pipeline Deteksi Dinamika Garis Pantai Parangtritis (1996 - 2026)
"""
import os
import ee
import geemap
import config as cfg
import preprocessing as prep
import segmentation as seg
import change_detection as cd

# =========================================================================
# 1. SETUP STRUKTUR FOLDER OUTPUT LOKAL
# =========================================================================
dirs = {
    'html': 'outputs/html',
    'geotiff': 'outputs/geotiff'
}
for path in dirs.values():
    os.makedirs(path, exist_ok=True)

print("Memulai komputasi Earth Engine untuk seluruh tahun (1996 - 2026)...")

# Inisialisasi Kanvas Peta Interaktif
Map = geemap.Map(center=[-8.0260, 110.3340], zoom=15)
Map.add_basemap('HYBRID')

# =========================================================================
# 2. EKSTRAKSI GARIS DARATAN SEMUA TAHUN (7 TITIK WAKTU)
# =========================================================================
land_dict = {}

for idx, year in enumerate(cfg.year_list):
    mndwi = prep.get_annual_mndwi(year, cfg.roi)
    land = seg.extract_land_mask(mndwi, cfg.mndwi_threshold, cfg.morph_radius)
    land_dict[year] = land
    
    # Tambahkan layer daratan tahunan (default: uncheck di panel layers)
    Map.addLayer(
        land.selfMask(), 
        {'palette': [cfg.palette['land_years'][idx]]}, 
        f'Daratan Tahun {year}', 
        False
    )
    print(f"-> Garis daratan tahun {year} berhasil diekstraksi.")

# =========================================================================
# 3. DETEKSI SPASIAL INTERVAL 5 TAHUNAN (SEMUA PERIODE LENGKAP)
# =========================================================================
abrasi_layers = []
akresi_layers = []

for i in range(len(cfg.year_list) - 1):
    y1 = cfg.year_list[i]
    y2 = cfg.year_list[i + 1]
    
    abr = cd.detect_abrasi(land_dict[y1], land_dict[y2])
    akr = cd.detect_akresi(land_dict[y1], land_dict[y2])
    
    abrasi_layers.append(abr)
    akresi_layers.append(akr)
    
    # Layer Akresi per periode (Pendukung - default off)
    Map.addLayer(
        akr.selfMask(), 
        {'palette': [cfg.palette['akresi_periode'][i]]}, 
        f'Akresi {y1}-{y2} (Pendukung)', 
        False
    )
    
    # Layer Abrasi per periode (Utama - default off)
    Map.addLayer(
        abr.selfMask(), 
        {'palette': [cfg.palette['abrasi_periode'][i]]}, 
        f'Abrasi {y1}-{y2} [Utama]', 
        False
    )

# =========================================================================
# 4. AGREGASI JEJAK KUMULATIF 30 TAHUN (1996 - 2026)
# =========================================================================
total_abrasi = cd.combine_cumulative(abrasi_layers)
total_akresi = cd.combine_cumulative(akresi_layers)

# Layer Garis Acuan
Map.addLayer(land_dict[1996].selfMask(), {'palette': [cfg.palette['daratan_base']]}, 'Daratan Dasar 1996', False)
Map.addLayer(land_dict[2026].selfMask(), {'palette': [cfg.palette['daratan_akhir']]}, 'Daratan Terkini 2026', False)

# LAYER TAMPILAN UTAMA (Default Aktif)
Map.addLayer(total_akresi, {'palette': [cfg.palette['total_akresi']]}, 'PENDUKUNG: Total Jejak Akresi (1996-2026)', True)
Map.addLayer(total_abrasi, {'palette': [cfg.palette['total_abrasi']]}, 'UTAMA: TOTAL JEJAK ABRASI (1996-2026)', True)

# =========================================================================
# 5. PANEL LEGENDA INTERAKTIF PETA
# =========================================================================
legend_dict = {
    'Jejak Abrasi (Fokus Utama)': cfg.palette['total_abrasi'],
    'Jejak Akresi (Pendukung)': cfg.palette['total_akresi']
}
Map.add_legend(title='Dinamika Pantai Parangtritis', legend_dict=legend_dict, position='bottomleft')

# =========================================================================
# 6. PENYIMPANAN OUTPUT TERSTRUKTUR
# =========================================================================
# A. Simpan Peta Interaktif HTML Mandiri
html_file = os.path.join(dirs['html'], 'peta_dinamika_parangtritis_1996_2026.html')
Map.to_html(html_file)
print(f"\n[SUKSES] Peta HTML interaktif tersimpan di: {html_file}")

# B. Ekspor Citra Raster GeoTIFF (Resolusi 30 m)
print("Mengekspor GeoTIFF hasil analisis ke folder 'outputs/geotiff/'...")
geotiff_abrasi = os.path.join(dirs['geotiff'], 'abrasi_kumulatif_1996_2026.tif')
geotiff_akresi = os.path.join(dirs['geotiff'], 'akresi_kumulatif_1996_2026.tif')

geemap.ee_export_image(
    total_abrasi.unmask(0).toByte(),
    filename=geotiff_abrasi,
    scale=30,
    region=cfg.roi,
    file_per_band=False
)
print(f"[SUKSES] GeoTIFF Abrasi tersimpan: {geotiff_abrasi}")

geemap.ee_export_image(
    total_akresi.unmask(0).toByte(),
    filename=geotiff_akresi,
    scale=30,
    region=cfg.roi,
    file_per_band=False
)
print(f"[SUKSES] GeoTIFF Akresi tersimpan: {geotiff_akresi}")
print("\nSemua proses selesai. Seluruh tahun (1996-2026) berhasil dipetakan dan diekspor dengan rapi.")