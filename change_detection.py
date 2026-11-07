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