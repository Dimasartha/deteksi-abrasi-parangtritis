"""
preprocessing.py: Cloud Masking QA_PIXEL dan Komposit Median Tahunan Lintas Sensor
"""
import ee

l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')

def mask_tm(image):
    """Masking awan dan bayangan untuk Landsat 5/7 (TM/ETM+)."""
    qa = image.select('QA_PIXEL')
    mask = (qa.bitwiseAnd(1 << 1).eq(0)
            .And(qa.bitwiseAnd(1 << 3).eq(0))
            .And(qa.bitwiseAnd(1 << 4).eq(0)))
    
    # Landsat 5/7: Green = SR_B2, SWIR1 = SR_B5
    green = image.select('SR_B2').multiply(0.0000275).add(-0.2)
    swir  = image.select('SR_B5').multiply(0.0000275).add(-0.2)
    
    mndwi = green.subtract(swir).divide(green.add(swir)).rename('MNDWI')
    return mndwi.updateMask(mask)

def mask_oli(image):
    """Masking awan, cirrus, dan bayangan untuk Landsat 8/9 (OLI/OLI-2)."""
    qa = image.select('QA_PIXEL')
    mask = (qa.bitwiseAnd(1 << 1).eq(0)
            .And(qa.bitwiseAnd(1 << 2).eq(0))
            .And(qa.bitwiseAnd(1 << 3).eq(0))
            .And(qa.bitwiseAnd(1 << 4).eq(0)))
    
    # Landsat 8/9: Green = SR_B3, SWIR1 = SR_B6
    green = image.select('SR_B3').multiply(0.0000275).add(-0.2)
    swir  = image.select('SR_B6').multiply(0.0000275).add(-0.2)
    
    mndwi = green.subtract(swir).divide(green.add(swir)).rename('MNDWI')
    return mndwi.updateMask(mask)

def get_annual_mndwi(year, roi):
    """Membuat komposit median MNDWI bebas awan sesuai era satelit."""
    start = ee.Date.fromYMD(year, 1, 1)
    end   = ee.Date.fromYMD(year, 12, 31)
    
    if year < 2014:
        # Era 1996 - 2011 menggunakan gabungan Landsat 5 TM & Landsat 7 ETM+
        col = l5.merge(l7).filterBounds(roi).filterDate(start, end).map(mask_tm)
    else:
        # Era 2016 - 2026 menggunakan gabungan Landsat 8 OLI & Landsat 9 OLI-2
        col = l8.merge(l9).filterBounds(roi).filterDate(start, end).map(mask_oli)
        
    return col.median().clip(roi)