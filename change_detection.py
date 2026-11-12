"""
change_detection.py: Deteksi Selisih Spasial Multitemporal dan Agregasi Kumulatif
"""
import ee

def detect_abrasi(land_t1, land_t2):
    """Abrasi: Tahun T1 Daratan (1), namun pada Tahun T2 hilang menjadi Laut (0)."""
    return land_t1.eq(1).And(land_t2.eq(0))

def detect_akresi(land_t1, land_t2):
    """Akresi: Tahun T1 Laut (0), namun pada Tahun T2 bertambah menjadi Daratan (1)."""
    return land_t1.eq(0).And(land_t2.eq(1))

def combine_cumulative(layer_list):
    """Menggabungkan seluruh kejadian piksel historis sepanjang periode (Spatial Union / OR)."""
    cumulative = layer_list[0].unmask(0)
    for layer in layer_list[1:]:
        cumulative = cumulative.Or(layer.unmask(0))
    return cumulative.selfMask()


def calculate_area(binary_mask, roi, scale=30):
    """
    Menghitung luas area (meter persegi dan hektar) dari mask biner di dalam ROI.
    Setiap piksel bernilai 1 dikalikan dengan bobot luas fisik aktual dari ee.Image.pixelArea().
    """
    mask = binary_mask.unmask(0).eq(1)
    area_img = mask.multiply(ee.Image.pixelArea()).rename('area')

    stats = area_img.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=roi,
        scale=scale,
        maxPixels=1e9
    )

    val = stats.get('area').getInfo()
    m2 = float(val) if val is not None else 0.0
    hectares = m2 / 10000.0

    return {
        'm2': m2,
        'ha': hectares
    }
