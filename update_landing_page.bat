@echo off
title Script Update Total Landing Page (Ammar Hanafi)
color 0B

echo ========================================================================
echo        OTO-UPDATE TOTAL LANDING PAGE KE VERCEL (AMMAR HANAFI)
echo ========================================================================
echo.

echo [LANGKAH 1] Sinkronisasi PDF Skripsi...
copy /Y "d:\Skripsi\my\induk.pdf" "d:\Skripsi\my\landing-page\public\skrp_doc_vault_9x.dat"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal menyalin PDF. Pastikan file tidak sedang dibuka.
) else (
    echo -- PDF Berhasil disinkronkan! --
)
echo.

echo [LANGKAH 2] Ekstraksi Rumus Terbaru dari Landasan Teori...
python "d:\Skripsi\my\extract_eqs.py"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal mengekstrak rumus.
) else (
    echo -- Rumus Berhasil diperbarui! --
)
echo.

echo [LANGKAH 3] Sinkronisasi Gambar ^& Tabel Hasil Analisis...
python "d:\Skripsi\my\prepare_landing_assets.py"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal sinkronisasi aset galeri.
) else (
    echo -- Galeri Berhasil diperbarui! --
)
echo.

echo [LANGKAH 4] Menyimpan pembaruan ke Git ^& GitHub...
cd /d "d:\Skripsi\my"
git add .
git commit -m "Full auto-update landing page: PDF, Formulas, and Gallery Assets"
git push origin main
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal mengirim ke GitHub. Periksa koneksi internet.
) else (
    echo.
    echo ========================================================================
    echo TOTAL UPDATE SUKSES! 🚀
    echo Website sedang dibangun ulang oleh Vercel.
    echo Tunggu 1-2 menit untuk melihat seluruh perubahan terbaru.
    echo ========================================================================
)
echo.
pause
