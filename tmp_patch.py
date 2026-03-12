import sys
import os

target = r"d:\Skripsi\my\web\skripsiv2\app.py"

with open(target, 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Fix Fiona Error by using pyogrio
code = code.replace(
    'gdf = gpd.read_file("gadm41_IDN_2.shp")',
    'gdf = gpd.read_file("gadm41_IDN_2.shp", engine="pyogrio")'
)

# 2. Swap Eigendecomposition with SVD
svd_orig = """    # 6. Dekomposisi Wc (Mendapatkan Skor Fc)
    eig_vals_c, eig_vecs_c = np.linalg.eig(Wc)
    eig_vals_c, eig_vecs_c = np.real(eig_vals_c), np.real(eig_vecs_c)"""

svd_new = """    # 6. Dekomposisi Wc (Mendapatkan Skor Fc) menggunakan SVD
    # Memperbaiki error kompleks di server linux (Hugging Face)
    U, S, Vt = np.linalg.svd(Wc)
    eig_vals_c = S
    eig_vecs_c = U"""

code = code.replace(svd_orig, svd_new)

# 3. Add Spatial Text Labels to maps
text_label_map_t1 = """
        fig_map_t1.update_layout(title="", margin={"r":0,"t":0,"l":0,"b":0})
"""
text_label_map_t1_new = """
        fig_map_t1.update_layout(title="", margin={"r":0,"t":0,"l":0,"b":0})
        # Add Text Labels
        lon_list, lat_list, text_list = [], [], []
        for _, row in df_map_t1.iterrows():
            area = row['Kab/Kota']
            geom = gdf[gdf['id_cocok'] == area]
            if not geom.empty:
                lon_list.append(geom.geometry.centroid.x.values[0])
                lat_list.append(geom.geometry.centroid.y.values[0])
                text_list.append(area)
        if text_list:
            fig_map_t1.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))
"""
code = code.replace(text_label_map_t1, text_label_map_t1_new)

text_label_map_t2 = """
        fig_map_t2.update_layout(title="", margin={"r":0,"t":0,"l":0,"b":0})
"""
text_label_map_t2_new = """
        fig_map_t2.update_layout(title="", margin={"r":0,"t":0,"l":0,"b":0})
        # Add Text Labels
        lon_list2, lat_list2, text_list2 = [], [], []
        for _, row in df_map_t2.iterrows():
            area = row['Kab/Kota']
            geom = gdf[gdf['id_cocok'] == area]
            if not geom.empty:
                lon_list2.append(geom.geometry.centroid.x.values[0])
                lat_list2.append(geom.geometry.centroid.y.values[0])
                text_list2.append(area)
        if text_list2:
            fig_map_t2.add_trace(go.Scattermapbox(lon=lon_list2, lat=lat_list2, mode='text', text=text_list2, textfont=dict(size=9, color='black'), showlegend=False))
"""
code = code.replace(text_label_map_t2, text_label_map_t2_new)

text_label_comp_map = """
        fig_map.update_layout(title=title_text, margin={"r":0,"t":40,"l":0,"b":0})
"""
text_label_comp_map_new = """
        fig_map.update_layout(title=title_text, margin={"r":0,"t":40,"l":0,"b":0})
        # Add Text Labels
        lon_list_c, lat_list_c, text_list_c = [], [], []
        for _, row in df_map.iterrows():
            area = row['Kab/Kota']
            geom = gdf[gdf['id_cocok'] == area]
            if not geom.empty:
                lon_list_c.append(geom.geometry.centroid.x.values[0])
                lat_list_c.append(geom.geometry.centroid.y.values[0])
                text_list_c.append(area)
        if text_list_c:
            fig_map.add_trace(go.Scattermapbox(lon=lon_list_c, lat=lat_list_c, mode='text', text=text_list_c, textfont=dict(size=9, color='black'), showlegend=False))
"""
code = code.replace(text_label_comp_map, text_label_comp_map_new)

# Generate centroids in the gdf right after load
centroid_orig = """    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.005, preserve_topology=True)
    # KONVERSI KE GEOJSON"""
centroid_new = """    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.005, preserve_topology=True)
    # Centroid calculation for text labels
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gdf['centroid_lon'] = gdf.geometry.centroid.x
        gdf['centroid_lat'] = gdf.geometry.centroid.y
    # KONVERSI KE GEOJSON"""
code = code.replace(centroid_orig, centroid_new)

# Fix requirements logic
with open(target, 'w', encoding='utf-8') as f:
    f.write(code)
print("Patcher script finished successfully.")
