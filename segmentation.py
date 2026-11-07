"""
segmentation.py: Ambangan Biner MNDWI dan Operasi Morfologi Citra (Opening)
"""
import ee

def extract_land_mask(mndwi_image, threshold=0.05, radius=1):
    """
    Segmentasi biner garis pantai:
    1. Thresholding: MNDWI > 0.05 adalah Air Laut
    2. Morfologi Opening (focalMin -> focalMax) mereduksi derau buih ombak
    3. Inversi: Piksel bukan air adalah Daratan (1)
    """
    kernel = ee.Kernel.circle(radius=radius)
    
    # Air mentah (1 = Air, 0 = Non-air)
    water_raw = mndwi_image.gt(threshold)
    
    # Operasi Opening: Erosi dilanjutkan Dilasi
    water_clean = (water_raw.focalMin(kernel=kernel, iterations=1)
                            .focalMax(kernel=kernel, iterations=1))
    
    # Daratan = Inversi air laut (1 = Daratan, 0 = Air Laut)
    return water_clean.eq(0).rename('land')