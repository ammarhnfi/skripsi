import os
import json
import shutil

src = r"d:\Skripsi\my\output_app"
dest = r"d:\Skripsi\my\landing-page\public\output_app"
manifest_path = r"d:\Skripsi\my\landing-page\public\output_app_manifest.json"

if not os.path.exists(dest):
    os.makedirs(dest)

files = os.listdir(src)
manifest = []

# Grouping logic
def get_group(fname):
    if fname.startswith('biplot_tahun'): return 'Snapshot Biplot'
    if fname.startswith('boxplot'): return 'Distribusi Variabel'
    if fname.startswith('cluster_biplot'): return 'Biplot Klaster'
    if fname.startswith('cluster_map'): return 'Peta Klaster'
    if fname.startswith('dendrogram'): return 'Dendrogram'
    if fname.startswith('elbow_plot'): return 'Elbow Plot'
    if fname.startswith('output_table'): return 'Tabel Hasil (.tex)'
    if fname in ['compromise_map.png', 'loading_plot.png', 'rv_heatmap.png', 'scree_plot.png', 'statis_trajectories.png', 'variable_contribution.png', 'variable_cos2.png', 'permutation_histogram.png']:
        return 'Hasil Utama STATIS'
    return 'Lain-lain'

for f in files:
    if f == 'OUTPUT_APP.md': continue
    src_f = os.path.join(src, f)
    if os.path.isfile(src_f):
        # Determine type
        ftype = 'image' if f.endswith('.png') else 'text' if f.endswith('.tex') else 'other'
        manifest.append({
            'name': f,
            'caption': f.replace('_', ' ').replace('.png', '').replace('.tex', '').title(),
            'type': ftype,
            'src': f'/output_app/{f}',
            'group': get_group(f)
        })
        # Copy file
        shutil.copy2(src_f, os.path.join(dest, f))

# Sort manifest by group then caption
manifest.sort(key=lambda x: (x['group'], x['caption']))

from datetime import datetime
import locale

# Set locale for Indonesian day names if possible (safe fallback provided)
try:
    locale.setlocale(locale.LC_TIME, 'id_ID.utf8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Indonesian_Indonesia.1252')
    except:
        pass

# Generate Last Update timestamp
now = datetime.now()
timestamp_str = now.strftime("%A, %d %B %Y %H:%M:%S") + " WIB"
update_info_path = r"d:\Skripsi\my\landing-page\public\last_update.json"

with open(update_info_path, "w", encoding="utf-8") as f:
    json.dump({"lastUpdate": timestamp_str}, f, indent=2)

print(f"Copied {len(manifest)} files and generated manifest + last_update.json.")
