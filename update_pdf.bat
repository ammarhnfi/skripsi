@echo off
title Script Update Skripsi PDF (Ammar Hanafi)
color 0B

echo ========================================================================
echo        OTO-UPDATE REVISI SKRIPSI PDF KE VERCEL (AMMAR HANAFI)
echo ========================================================================
echo.

echo [LANGKAH 1] Menyalin file induk.pdf terbaru menuju brankas sistem...
copy /Y "d:\Skripsi\my\induk.pdf" "d:\Skripsi\my\landing-page\public\skrp_doc_vault_9x.dat"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal menyalin file. Pastikan induk.pdf tidak sedang dibuka di aplikasi pdf editor.
    pause
    exit /b
)
echo -- Proses copy berhasil! --
echo.

echo [LANGKAH 2] Menyimpan pembaruan dan menyiapkan jalur ke GitHub...
cd /d "d:\Skripsi\my"
git add .
git commit -m "Auto-update revisi PDF Skripsi terbaru ke Landing Page"
if %ERRORLEVEL% NEQ 0 (
    echo -- Tidak ada perubahan file baru yang terdeteksi untuk di-push --
)
echo.

echo [LANGKAH 3] Mengirim (Pushing) kode ke GitHub dan Memicu Vercel...
git push origin main
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal mengirim ke GitHub. Pastikan Anda punya koneksi internet.
    pause
    exit /b
)
echo.

echo ========================================================================
echo SELAMAT! PEMBARUAN SUKSES DIKIRIM KE AWAN! 🚀
echo Vercel akan menangkap pembaruan ini dan me-redeploy web Anda.
echo Cukup tunggu 1 hingga 2 menit agar PDF dirender sempurna di halaman web.
echo ========================================================================
echo.
pause
