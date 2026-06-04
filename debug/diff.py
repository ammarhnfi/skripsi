import filecmp

dir1 = "D:/skripsi/my/output_sample/scenario1"
dir2 = "D:/skripsi/my/output_sample2/scenario1"

perbandingan = filecmp.dircmp(dir1, dir2)

print("File yang sama persis:")
print(perbandingan.same_files)

print("\nFile yang isinya berbeda:")
print(perbandingan.diff_files)

print("\nHanya ada di Folder 1:")
print(perbandingan.left_only)

print("\nHanya ada di Folder 2:")
print(perbandingan.right_only)

import os

def cek_total_folder(path):
    total_size = 0
    total_files = 0
    total_dirs = 0

    for dirpath, dirnames, filenames in os.walk(path):
        total_dirs += len(dirnames)
        total_files += len(filenames)
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # Skip jika file adalah symlink
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    size_mb = total_size / (1024 * 1024)
    return total_files, total_dirs, round(size_mb, 2)

# Eksekusi
file1, dir1, size1 = cek_total_folder(dir1)
print(f"Folder 1 -> Files: {file1}, Folders: {dir1}, Size: {size1} MB")


file2, dir2, size2 = cek_total_folder(dir2)
print(f"Folder 2 -> Files: {file2}, Folders: {dir2}, Size: {size2} MB")