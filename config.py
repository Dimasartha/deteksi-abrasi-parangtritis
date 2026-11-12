"""
config.py: Konfigurasi Parameter Spasial, Temporal, dan Palet Visualisasi
"""
import ee

# Inisialisasi API Earth Engine
ee.Initialize()

# ROI Garis Pantai Parangtritis (Panjang bentang ±2.600 m, tanpa muara Kali Opak)
roi_coords = [
    [110.3230, -8.0210],
    [110.3450, -8.0210],
    [110.3450, -8.0310],
    [110.3230, -8.0310],
    [110.3230, -8.0210]
]
roi = ee.Geometry.Polygon([roi_coords])
_lons = [pt[0] for pt in roi_coords]
_lats = [pt[1] for pt in roi_coords]
roi_bounds = (min(_lons), max(_lons), min(_lats), max(_lats))

# Daftar 7 Titik Tahun Pengamatan (Interval 5 Tahunan: 1996 - 2026)
year_list = [1996, 2001, 2006, 2011, 2016, 2021, 2026]

# Parameter Segmentasi dan Morfologi Citra (Task III Modul Praktikum)
mndwi_threshold = 0.05
morph_radius = 1

# Parameter Visualisasi True Color RGB per Era Sensor (Sentinel-2 & Landsat)
rgb_export_scale = 10  # Resolusi ekspor citra RGB 10 meter/piksel (Sentinel-2 & Pansharpened)
rgb_vis_sr = {'bands': ['R', 'G', 'B'], 'min': 0.0, 'max': 0.3, 'gamma': 1.2}
rgb_vis_toa = {'bands': ['R', 'G', 'B'], 'min': 0.04, 'max': 0.32, 'gamma': 1.25}

# Konfigurasi Palet Visualisasi Peta
palette = {
    # 7 Warna unik untuk daratan masing-masing tahun
    'land_years': ['#4B0082', '#0000FF', '#00FFFF', '#008000', '#FFFF00', '#FFA500', '#FFFFFF'],
    
    # 6 Warna gradasi untuk interval 5 tahunan (1996-2001 s.d. 2021-2026)
    'abrasi_periode': ['#9c27b0', '#3f51b5', '#03a9f4', '#ffeb3b', '#ff9800', '#e91e63'],
    'akresi_periode': ['#b2ebf2', '#80deea', '#4dd0e1', '#26c6da', '#00bcd4', '#0097a7'],
    
    # Palet Tampilan Utama Kumulatif 30 Tahun
    'total_abrasi': '#FF0000',    # Merah pekat (Fokus Utama)
    'total_akresi': '#00E5FF',    # Cyan / Biru terang (Pendukung)
    'daratan_base': '#CCCCCC',    # Abu-abu (Daratan Awal 1996)
    'daratan_akhir': '#FFFFFF'    # Putih (Daratan Terkini 2026)
}