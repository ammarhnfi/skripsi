import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'd:\Skripsi\my\Presentation\sidang_skripsi.html'
with open(path, encoding='utf-8') as f:
    content = f.read()

old = '''            <table class="dtable" style="margin-top:10px;font-size:.75rem;">
              <thead><tr><th>KMO</th><th>Kategori</th></tr></thead>
              <tbody>
                <tr><td>≥ 0,90</td><td>Marvelous (Sangat Baik)</td></tr>
                <tr><td>0,80 – 0,89</td><td>Meritorious (Baik)</td></tr>
                <tr><td>0,70 – 0,79</td><td>Middling (Sedang)</td></tr>
                <tr><td>0,60 – 0,69</td><td>Mediocre (Cukup)</td></tr>
                <tr><td>&lt; 0,50</td><td>Unacceptable ❌</td></tr>
              </tbody>
            </table>'''

new = '''            <table class="dtable" style="margin-top:10px;font-size:.55em;">
              <thead><tr><th>Nilai <em>KMO</em></th><th>Kategori Penilaian</th></tr></thead>
              <tbody>
                <tr><td>0,8 ≤ <em>KMO</em> ≤ 1,0</td><td>Data sangat memadai</td></tr>
                <tr><td>0,7 ≤ <em>KMO</em> &lt; 0,8</td><td>Data memadai</td></tr>
                <tr><td>0,6 ≤ <em>KMO</em> &lt; 0,7</td><td>Data cukup</td></tr>
                <tr><td>0,5 ≤ <em>KMO</em> &lt; 0,6</td><td>Data tidak memadai</td></tr>
                <tr><td><em>KMO</em> &lt; 0,5</td><td>Data tidak dapat digunakan</td></tr>
              </tbody>
            </table>'''

if old not in content:
    print("ERROR: old string not found")
    import sys; sys.exit(1)

content = content.replace(old, new, 1)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Done.")
