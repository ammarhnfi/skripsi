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

with open(manifest_path, "w", encoding="utf-8") as j:
    json.dump(manifest, j, indent=2)

print(f"Copied {len(manifest)} files to public/output_app and generated manifest.")
