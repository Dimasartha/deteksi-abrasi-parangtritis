"""
visualization.py: Pembuatan Peta HTML Interaktif (Folium/Leaflet) dan Output PNG Resolusi Tinggi
"""
import folium
from branca.element import Element
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from PIL import Image


def load_rgb_geotiff(geotiff_path):
    """Membaca GeoTIFF RGB (uint8) menjadi array NumPy (H, W, 3)."""
    with Image.open(geotiff_path) as img:
        return np.asarray(img.convert('RGB'))


def save_year_png(rgb_array, year, sensor_label, roi_bounds, output_path):
    """Menyimpan citra satelit True Color satu tahun ke format PNG dengan koordinat geografis."""
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    ax.imshow(rgb_array, extent=roi_bounds, interpolation='bicubic', aspect='equal')
    ax.set_title(
        f'Citra Satelit Pantai Parangtritis - Tahun {year}\n'
        f'({sensor_label} | Komposit Median RGB)',
        fontsize=11,
        fontweight='bold',
        pad=10,
    )
    ax.set_xlabel('Bujur (°BT)', fontsize=9)
    ax.set_ylabel('Lintang (°LS)', fontsize=9)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter('%.3f'))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.3f'))
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def save_comparison_png(yearly_images, roi_bounds, output_path):
    """Menyimpan panel perbandingan seluruh citra satelit (1996 - 2026) dalam satu PNG."""
    n_items = len(yearly_images)
    ncols = 4
    nrows = (n_items + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 2.7 * nrows + 0.8), dpi=300)
    axes_flat = np.atleast_1d(axes).ravel()

    for idx, (year, sensor_label, rgb_array) in enumerate(yearly_images):
        ax = axes_flat[idx]
        ax.imshow(rgb_array, extent=roi_bounds, interpolation='bicubic', aspect='equal')
        ax.set_title(f'{year} — {sensor_label}', fontsize=9.5, fontweight='bold')
        ax.set_xticks([])
        ax.set_yticks([])

    for idx in range(n_items, len(axes_flat)):
        axes_flat[idx].axis('off')

    fig.suptitle(
        'Perkembangan Citra Satelit Pantai Parangtritis (1996 - 2026, Interval 5 Tahun)',
        fontsize=13,
        fontweight='bold',
        y=0.98,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)


def create_interactive_map(center=(-8.0260, 110.3340), zoom=15):
    """Membuat kanvas peta Folium murni agar kontrol layer 100% interaktif di browser."""
    m = folium.Map(location=list(center), zoom_start=zoom, tiles=None, control_scale=True)

    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Hybrid (Basemap)',
        overlay=False,
        control=True,
        show=True,
        max_zoom=22,
    ).add_to(m)

    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Satellite (Basemap)',
        overlay=False,
        control=True,
        show=False,
        max_zoom=22,
    ).add_to(m)

    folium.TileLayer(
        tiles='OpenStreetMap',
        name='OpenStreetMap (Basemap)',
        overlay=False,
        control=True,
        show=False,
    ).add_to(m)

    folium.map.CustomPane('satellite_pane', z_index=250).add_to(m)
    folium.map.CustomPane('analysis_pane', z_index=450).add_to(m)
    return m


def add_ee_layer(m, ee_image, vis_params, name, show=False, pane='analysis_pane'):
    """Menambahkan layer Earth Engine ke peta Folium sebagai TileLayer interaktif."""
    map_id_dict = ee_image.getMapId(vis_params)
    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        name=name,
        overlay=True,
        control=True,
        show=show,
        pane=pane,
        max_zoom=22,
    ).add_to(m)


def finalize_interactive_map(m, legend_title, legend_dict, output_html):
    """Menambahkan kontrol layer, legenda, dan perilaku bring-to-front lalu menyimpan HTML."""
    folium.LayerControl(position='topright', collapsed=False).add_to(m)

    items_html = ''.join(
        f'<div style="display:flex;align-items:center;margin:4px 0;">'
        f'<span style="display:inline-block;width:14px;height:14px;background:{color};'
        f'border:1px solid #444;margin-right:8px;flex-shrink:0;"></span>'
        f'<span>{label}</span></div>'
        for label, color in legend_dict.items()
    )
    legend_html = (
        '<div style="position:fixed;bottom:28px;left:16px;z-index:1000;'
        'background:rgba(255,255,255,0.92);padding:10px 14px;border-radius:6px;'
        'box-shadow:0 2px 6px rgba(0,0,0,0.28);font-family:Arial,sans-serif;font-size:12px;">'
        f'<div style="font-weight:bold;margin-bottom:6px;font-size:13px;">{legend_title}</div>'
        f'{items_html}'
        '<div style="margin-top:6px;color:#555;font-size:11px;">'
        'Centang layer di panel kanan untuk menampilkan/menyembunyikan citra.'
        '</div></div>'
    )
    m.get_root().html.add_child(Element(legend_html))

    # Pastikan kontrol layer bisa di-scroll rapi jika daftar layer panjang
    style_css = (
        '<style>'
        '.leaflet-control-layers-overlays { max-height: 72vh; overflow-y: auto; padding-right: 4px; }'
        '</style>'
    )
    m.get_root().header.add_child(Element(style_css))

    # Pastikan citra satelit yang baru dicentang tampil di atas citra satelit lain yang aktif
    map_var = m.get_name()
    bring_front_js = (
        '<script>'
        'window.addEventListener("load", function() {'
        f'  var mapObj = window["{map_var}"];'
        '  if (!mapObj) return;'
        '  mapObj.on("overlayadd", function(e) {'
        '    if (e.name && e.name.indexOf("Citra Satelit") === 0 && e.layer && e.layer.bringToFront) {'
        '      e.layer.bringToFront();'
        '    }'
        '  });'
        '});'
        '</script>'
    )
    m.get_root().html.add_child(Element(bring_front_js))
    m.save(output_html)
