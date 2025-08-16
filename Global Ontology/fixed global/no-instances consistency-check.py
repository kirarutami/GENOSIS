# Pastikan Anda telah menginstal owlready2: pip install owlready2
# Anda mungkin juga perlu menginstal Java Development Kit (JDK) agar HermiT reasoner berfungsi.
import owlready2
from owlready2 import *
import os # Digunakan untuk memeriksa apakah file ada

def check_consistency(ontology_file):
    """
    Fungsi untuk memeriksa konsistensi ontologi menggunakan HermiT reasoner.

    Args:
        ontology_file (str): Path ke file ontologi (format .owl atau .rdf).

    Returns:
        bool: True jika ontologi konsisten, False jika tidak.
    """
    try:
        # Load ontologi
        # Menggunakan "file://" untuk memastikan path diinterpretasikan dengan benar,
        # terutama pada sistem operasi yang berbeda.
        print(f"Memuat ontologi dari file: {ontology_file}")
        # Mengonversi backslash menjadi forward slash untuk kompatibilitas path URI
        ontology_uri = "file://" + ontology_file.replace("\\", "/")
        onto = get_ontology(ontology_uri).load()

        # Gunakan HermiT reasoner (default dalam owlready2)
        # Owlready2 akan mencoba menjalankan HermiT.
        # Pastikan Java terinstal dan ada di PATH sistem Anda jika HermiT tidak ditemukan secara otomatis.
        print("Menyinkronkan dengan HermiT reasoner...")
        with onto:
            # sync_reasoner_hermit() bisa digunakan jika Anda ingin eksplisit
            # atau jika ada konfigurasi reasoner lain.
            # Untuk HermiT sebagai default, sync_reasoner() sudah cukup.
            sync_reasoner(debug=0)

        # Periksa konsistensi
        print("Memeriksa konsistensi...")
        # Mencari kelas-kelas yang tidak konsisten di dalam world default
        inconsistent_classes = list(default_world.inconsistent_classes())

        if not inconsistent_classes:
            print("\n✅ Ontologi KONSISTEN (tidak ditemukan inkonsistensi)")
            return True
        else:
            print("\n❌ Ontologi TIDAK KONSISTEN. Ditemukan kelas inkonsisten:")
            for cls in inconsistent_classes:
                print(f" - {cls}")
            return False

    except owlready2.base.OwlReadyInconsistentOntologyError as e:
        # Menangkap error spesifik jika ontologi tidak konsisten saat load
        print(f"\n❌ Ontologi TIDAK KONSISTEN saat dimuat: {str(e)}")
        # Menampilkan kelas-kelas yang tidak konsisten jika tersedia
        print("Kelas inkonsisten (jika terdeteksi oleh reasoner saat load):")
        for cls in default_world.inconsistent_classes():
            print(f" - {cls}")
        return False
    except Exception as e:
        # Menangkap semua error lain yang mungkin terjadi
        print(f"\n⚠️ Terjadi error saat memeriksa konsistensi: {str(e)}")
        print("Pastikan Java Development Kit (JDK) terinstal dan path-nya sudah benar.")
        print("Anda bisa mencoba menginstal JDK dan mengatur JAVA_HOME environment variable.")
        return False

def main():
    """
    Fungsi utama untuk menjalankan skrip pemeriksa konsistensi ontologi.
    """
    print("""
==========================================
  PEMERIKSA KONSISTENSI ONTOLOGI HERMIT
==========================================
""")

    # --- MODIFIKASI DI SINI ---
    # Masukkan path lengkap ke file ontologi Anda di bawah ini.
    # Contoh:
    # ontology_file_path = "D:\\thesis\\Global Ontology\\fixed global\\GSMFO.owl"
    # ontology_file_path = "/home/user/documents/ontology.owl"
    ontology_file_path = r"D:\thesis\Global Ontology\fixed global\GSMFO.owl"  # <--- GANTI PATH INI

    # Memeriksa apakah file ada
    if os.path.exists(ontology_file_path) and os.path.isfile(ontology_file_path):
        # Memeriksa apakah ekstensi file didukung
        if ontology_file_path.lower().endswith((".owl", ".rdf")):
            print(f"\nFile yang akan diperiksa: {ontology_file_path}")
            # Periksa konsistensi
            check_consistency(ontology_file_path)
        else:
            print(f"Format file tidak didukung: {ontology_file_path}")
            print("Harap pastikan path menunjuk ke file .owl atau .rdf.")
    else:
        print(f"File tidak ditemukan di path: {ontology_file_path}")
        print("Pastikan path file sudah benar dan file tersebut ada di lokasi tersebut.")
        print("Jika path mengandung backslash (\\), pastikan Anda menggunakan double backslash (\\\\) atau raw string (r\"...\").")


if __name__ == "__main__":
    # Mengatur path untuk owlready2 (opsional, jika ada masalah dengan penemuan Java/HermiT)
    owlready2.JAVA_EXE = r"C:\Program Files\Java\jdk-11\bin\java.exe" # Contoh: "C:\\Program Files\\Java\\jdk-11\\bin\\java.exe"
    main()
