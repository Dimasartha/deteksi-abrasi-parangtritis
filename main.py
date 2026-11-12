"""
main.py: Eksekusi Utama Pipeline Deteksi Dinamika Garis Pantai & Ekspor Citra Satelit Parangtritis (1996 - 2026)
"""
import os
import geemap
import config as cfg
import preprocessing as prep
import segmentation as seg
import change_detection as cd
import visualization as vis

# =========================================================================
# 1. SETUP STRUKTUR FOLDER OUTPUT LOKAL
# =========================================================================
dirs = {
    'html': 'outputs/html',
    'geotiff': 'outputs/geotiff',
    'png': 'outputs/png'
}
for path in dirs.values():
    os.makedirs(path, exist_ok=True)

print("Memulai komputasi Earth Engine untuk seluruh tahun (1996 - 2026)...")

# Inisialisasi Kanvas Peta Interaktif Berbasis Folium/Leaflet
Map = vis.create_interactive_map(center=(-8.0260, 110.3340), zoom=15)

# =========================================================================
# 2. EKSTRAKSI CITRA SATELIT RGB & GARIS DARATAN (7 TITIK WAKTU)
# =========================================================================
rgb_dict = {}
rgb_vis_dict = {}
land_dict = {}

for idx, year in enumerate(cfg.year_list):
    rgb = prep.get_annual_rgb(year, cfg.roi)
    vis_params = cfg.rgb_vis_sr if prep.is_sr_rgb(year) else cfg.rgb_vis_toa
    sensor_label = prep.get_sensor_label(year)
    rgb_dict[year] = rgb
    rgb_vis_dict[year] = vis_params

    # Layer Citra Satelit True Color per tahun (2026 aktif default, tahun lain bisa dicentang)
    vis.add_ee_layer(
        Map,
        rgb,
        vis_params,
        f'Citra Satelit {year} - {sensor_label}',
        show=(year == cfg.year_list[-1]),
        pane='satellite_pane',
    )

    mndwi = prep.get_annual_mndwi(year, cfg.roi)
    land = seg.extract_land_mask(mndwi, cfg.mndwi_threshold, cfg.morph_radius)
    land_dict[year] = land

    # Layer daratan tahunan (default: uncheck di panel layers)
    vis.add_ee_layer(
        Map,
        land.selfMask(),
        {'palette': [cfg.palette['land_years'][idx]]},
        f'Daratan Tahun {year}',
        show=False,
        pane='analysis_pane',
    )
    print(f"-> Citra satelit ({sensor_label}) & garis daratan tahun {year} berhasil disiapkan.")

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
    vis.add_ee_layer(
        Map,
        akr.selfMask(),
        {'palette': [cfg.palette['akresi_periode'][i]]},
        f'Akresi {y1}-{y2} (Pendukung)',
        show=False,
        pane='analysis_pane',
    )

    # Layer Abrasi per periode (Utama - default off)
    vis.add_ee_layer(
        Map,
        abr.selfMask(),
        {'palette': [cfg.palette['abrasi_periode'][i]]},
        f'Abrasi {y1}-{y2} [Utama]',
        show=False,
        pane='analysis_pane',
    )

# =========================================================================
# 4. AGREGASI JEJAK KUMULATIF 30 TAHUN (1996 - 2026)
# =========================================================================
total_abrasi = cd.combine_cumulative(abrasi_layers)
total_akresi = cd.combine_cumulative(akresi_layers)

# Layer Garis Acuan
vis.add_ee_layer(Map, land_dict[1996].selfMask(), {'palette': [cfg.palette['daratan_base']]}, 'Daratan Dasar 1996', show=False, pane='analysis_pane')
vis.add_ee_layer(Map, land_dict[2026].selfMask(), {'palette': [cfg.palette['daratan_akhir']]}, 'Daratan Terkini 2026', show=False, pane='analysis_pane')

# LAYER TAMPILAN UTAMA (Default Aktif)
vis.add_ee_layer(Map, total_akresi, {'palette': [cfg.palette['total_akresi']]}, 'PENDUKUNG: Total Jejak Akresi (1996-2026)', show=True, pane='analysis_pane')
vis.add_ee_layer(Map, total_abrasi, {'palette': [cfg.palette['total_abrasi']]}, 'UTAMA: TOTAL JEJAK ABRASI (1996-2026)', show=True, pane='analysis_pane')

# =========================================================================
# 5. SIMPAN PETA HTML INTERAKTIF & LEGENDA
# =========================================================================
legend_dict = {
    'Jejak Abrasi (Fokus Utama)': cfg.palette['total_abrasi'],
    'Jejak Akresi (Pendukung)': cfg.palette['total_akresi']
}
html_file = os.path.join(dirs['html'], 'peta_dinamika_parangtritis_1996_2026.html')
vis.finalize_interactive_map(Map, 'Dinamika Pantai Parangtritis', legend_dict, html_file)
print(f"\n[SUKSES] Peta HTML interaktif tersimpan di: {html_file}")

# =========================================================================
# 6. PENYIMPANAN OUTPUT GEOTIFF & PNG
# =========================================================================
# A. Ekspor Citra Raster GeoTIFF Analisis Abrasi & Akresi (Resolusi 30 m)
print("Mengekspor GeoTIFF hasil analisis abrasi/akresi ke folder 'outputs/geotiff/'...")
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

# B. Ekspor Citra Satelit True Color RGB (GeoTIFF 10 m & PNG) per Interval 5 Tahun
print(f"\nMengekspor citra satelit RGB resolusi {cfg.rgb_export_scale} m (1996 - 2026, interval 5 tahun)...")
yearly_png_inputs = []

for year in cfg.year_list:
    sensor_label = prep.get_sensor_label(year)
    geotiff_rgb = os.path.join(dirs['geotiff'], f'satelit_rgb_{year}.tif')
    png_rgb = os.path.join(dirs['png'], f'satelit_rgb_{year}.png')

    rgb_vis = (
        rgb_dict[year]
        .visualize(**rgb_vis_dict[year], forceRgbOutput=True)
        .unmask(0)
    )

    geemap.ee_export_image(
        rgb_vis,
        filename=geotiff_rgb,
        scale=cfg.rgb_export_scale,
        region=cfg.roi,
        file_per_band=False
    )
    if not os.path.exists(geotiff_rgb):
        raise RuntimeError(f"Gagal mengekspor GeoTIFF citra satelit tahun {year}: {geotiff_rgb}")

    rgb_array = vis.load_rgb_geotiff(geotiff_rgb)
    vis.save_year_png(rgb_array, year, sensor_label, cfg.roi_bounds, png_rgb)
    yearly_png_inputs.append((year, sensor_label, rgb_array))
    print(f"[SUKSES] Tahun {year} ({sensor_label}) -> {geotiff_rgb} & {png_rgb}")

comparison_png = os.path.join(dirs['png'], 'perbandingan_citra_1996_2026.png')
vis.save_comparison_png(yearly_png_inputs, cfg.roi_bounds, comparison_png)
print(f"[SUKSES] Panel perbandingan 1996-2026 tersimpan di: {comparison_png}")

print("\nSemua proses selesai. Citra satelit resolusi tinggi & peta HTML interaktif berhasil dibuat.")
