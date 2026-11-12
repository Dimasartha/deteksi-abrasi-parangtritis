"""
preprocessing.py: Cloud Masking, Komposit Median Tahunan, dan Peningkatan Resolusi Citra RGB
"""
import ee

l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
l7_toa = ee.ImageCollection('LANDSAT/LE07/C02/T1_TOA')
l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
s2_sr = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
s2_toa = ee.ImageCollection('COPERNICUS/S2_HARMONIZED')

_SR_SCALE = 0.0000275
_SR_OFFSET = -0.2


def _build_cloud_mask(image, mask_cirrus=False):
    """Membuat mask piksel bebas awan dan bayangan dari band QA_PIXEL Landsat."""
    qa = image.select('QA_PIXEL')
    mask = (
        qa.bitwiseAnd(1 << 1).eq(0)
        .And(qa.bitwiseAnd(1 << 3).eq(0))
        .And(qa.bitwiseAnd(1 << 4).eq(0))
    )
    if mask_cirrus:
        mask = mask.And(qa.bitwiseAnd(1 << 2).eq(0))
    return mask


def _scale_sr(image, bands):
    """Mengonversi nilai digital Surface Reflectance Collection 2 ke reflektansi."""
    return image.select(bands).multiply(_SR_SCALE).add(_SR_OFFSET)


def _compute_mndwi(image, green_band, swir_band, mask_cirrus=False):
    """Menghitung indeks MNDWI yang sudah dimask awan."""
    mask = _build_cloud_mask(image, mask_cirrus=mask_cirrus)
    green = _scale_sr(image, green_band)
    swir = _scale_sr(image, swir_band)
    mndwi = green.subtract(swir).divide(green.add(swir)).rename('MNDWI')
    return mndwi.updateMask(mask)


def mask_tm(image):
    """Masking awan dan bayangan untuk Landsat 5/7 (TM/ETM+) -> MNDWI."""
    return _compute_mndwi(image, 'SR_B2', 'SR_B5', mask_cirrus=False)


def mask_oli(image):
    """Masking awan, cirrus, dan bayangan untuk Landsat 8/9 (OLI/OLI-2) -> MNDWI."""
    return _compute_mndwi(image, 'SR_B3', 'SR_B6', mask_cirrus=True)


def mask_tm_rgb(image):
    """Masking awan dan ekstraksi True Color RGB untuk Landsat 5 SR (30 m, resample bicubic)."""
    mask = _build_cloud_mask(image, mask_cirrus=False)
    rgb = _scale_sr(image, ['SR_B3', 'SR_B2', 'SR_B1']).rename(['R', 'G', 'B'])
    return rgb.updateMask(mask).resample('bicubic')


def mask_l7_pansharpen_rgb(image):
    """Pansharpening HSV Landsat 7 TOA menggunakan band pankromatik B8 (15 m)."""
    mask = _build_cloud_mask(image, mask_cirrus=False)
    rgb_30m = image.select(['B3', 'B2', 'B1']).resample('bicubic')
    pan_15m = image.select('B8')
    hsv = rgb_30m.rgbToHsv()
    sharpened = ee.Image.cat([hsv.select('hue'), hsv.select('saturation'), pan_15m]).hsvToRgb()
    return sharpened.rename(['R', 'G', 'B']).updateMask(mask)


def _mask_s2_qa60(image):
    """Masking awan dan cirrus Sentinel-2 menggunakan bit QA60."""
    qa = image.select('QA60')
    return qa.bitwiseAnd(1 << 10).eq(0).And(qa.bitwiseAnd(1 << 11).eq(0))


def mask_s2_toa_rgb(image):
    """Masking awan dan ekstraksi True Color RGB Sentinel-2 TOA (10 m)."""
    mask = _mask_s2_qa60(image)
    rgb = image.select(['B4', 'B3', 'B2']).divide(10000).rename(['R', 'G', 'B'])
    return rgb.updateMask(mask)


def mask_s2_sr_rgb(image):
    """Masking awan/bayangan (QA60 + SCL) dan ekstraksi True Color RGB Sentinel-2 SR (10 m)."""
    scl = image.select('SCL')
    scl_mask = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    mask = _mask_s2_qa60(image).And(scl_mask)
    rgb = image.select(['B4', 'B3', 'B2']).divide(10000).rename(['R', 'G', 'B'])
    return rgb.updateMask(mask)


def get_annual_mndwi(year, roi):
    """Membuat komposit median MNDWI bebas awan sesuai era satelit."""
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    if year < 2014:
        col = l5.merge(l7).filterBounds(roi).filterDate(start, end).map(mask_tm)
    else:
        col = l8.merge(l9).filterBounds(roi).filterDate(start, end).map(mask_oli)
    return col.median().clip(roi)


def _get_rgb_spec(year):
    """Memilih sumber sensor beresolusi tertinggi yang tersedia untuk setiap tahun."""
    if year >= 2019:
        return s2_sr, mask_s2_sr_rgb, 'Sentinel-2 SR (10 m)', True
    if year >= 2016:
        return s2_toa, mask_s2_toa_rgb, 'Sentinel-2 TOA (10 m)', False
    if year >= 1999:
        return l7_toa, mask_l7_pansharpen_rgb, 'Landsat 7 Pan (15 m)', False
    return l5, mask_tm_rgb, 'Landsat 5 SR (30 m, Bicubic)', True


def get_sensor_label(year):
    """Mengembalikan label sensor dan resolusi spasial untuk tahun pengamatan."""
    return _get_rgb_spec(year)[2]


def is_sr_rgb(year):
    """Mengembalikan True jika citra RGB tahun tersebut berasal dari Surface Reflectance."""
    return _get_rgb_spec(year)[3]


def get_annual_rgb(year, roi):
    """Membuat komposit median True Color RGB bebas awan beresolusi tinggi."""
    start = ee.Date.fromYMD(year, 1, 1)
    end = ee.Date.fromYMD(year, 12, 31)
    collection, mapper, _, _ = _get_rgb_spec(year)
    col = collection.filterBounds(roi).filterDate(start, end).map(mapper)
    return col.median().clip(roi)
