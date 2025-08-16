# Pastikan Anda telah menginstal owlready2: pip install owlready2
# Anda mungkin juga perlu menginstal Java Development Kit (JDK) agar HermiT reasoner berfungsi.
import owlready2
from owlready2 import *
import os # Digunakan untuk memeriksa apakah file ada
import logging # Untuk mengontrol output logger Owlready2
import shutil # Untuk memeriksa keberadaan java (Python 3.3+)

# Menonaktifkan beberapa peringatan Owlready2 yang mungkin tidak relevan untuk output pengguna
# Anda bisa mengubah levelnya ke logging.INFO atau logging.DEBUG untuk lebih banyak detail dari Owlready2
logging.getLogger("owlready2").setLevel(logging.ERROR) # Cara yang lebih standar untuk mengatur logger library

def check_consistency_with_explanation(ontology_file):
    """
    Fungsi untuk memeriksa konsistensi ontologi menggunakan HermiT reasoner
    dan mencoba memberikan beberapa detail tentang inkonsistensi.
    Diasumsikan semua data (TBox dan ABox/instans) ada di ontology_file.

    Args:
        ontology_file (str): Path ke file ontologi utama (format .owl, .rdf, atau .xml).

    Returns:
        bool: True jika ontologi konsisten, False jika tidak.
    """
    world = World() # Membuat world baru untuk setiap pengecekan agar lebih bersih
    onto = None # Inisialisasi onto

    try:
        # Load ontologi utama (yang sekarang juga berisi instans)
        print(f"Memuat ontologi dari file: {ontology_file}")
        ontology_uri = "file://" + ontology_file.replace("\\", "/")
        onto = world.get_ontology(ontology_uri).load()
        
        print("Menyinkronkan dengan HermiT reasoner...")
        with world: # Menggunakan world dari ontologi yang dimuat
            # Untuk HermiT (default di Owlready2 jika Pellet tidak dikonfigurasi)
            sync_reasoner(infer_property_values=True, debug=0) 
            # Alternatif: Jika Anda memiliki Pellet dan ingin menggunakannya:
            # try:
            #     print("Mencoba menyinkronkan dengan Pellet reasoner...")
            #     sync_reasoner_pellet(infer_property_values=True, infer_data_property_values=True, debug=0)
            # except Exception as e_pellet:
            #     print(f"Gagal menggunakan Pellet ({e_pellet}), kembali ke HermiT (default)...")
            #     sync_reasoner(infer_property_values=True, debug=0)


        print("Memeriksa konsistensi...")
        inconsistent_classes = list(world.inconsistent_classes())

        if not inconsistent_classes:
            print("\n✅ Ontologi KONSISTEN (tidak ditemukan kelas inkonsisten dan tidak ada error inkonsistensi global).")
            # Tambahan: Periksa apakah owl:Nothing memiliki instans (seharusnya tidak jika konsisten)
            nothing_instances = list(owl.Nothing.instances(world=world))
            if nothing_instances:
                print("\n   PERINGATAN: Meskipun tidak ada kelas inkonsisten, owl.Nothing memiliki instans berikut (ini tidak seharusnya terjadi):")
                for ind_nothing in nothing_instances:
                    print(f"    - {ind_nothing.name}")
            return True
        else:
            print("\n❌ Ontologi TIDAK KONSISTEN. Ditemukan kelas inkonsisten (TBox atau akibat ABox):")
            for cls in inconsistent_classes:
                print(f" - {cls.name if hasattr(cls, 'name') else str(cls)}") # Menangani kelas anonim
            
            print("\n   Mencoba mencari individu yang mungkin terkait dengan kelas inkonsisten:")
            found_related_individual_in_inconsistent_class_check = False # Flag
            for cls in inconsistent_classes:
                cls_name = cls.name if hasattr(cls, 'name') else str(cls)
                if cls == owl.Nothing:
                    print(f"   - Kelas owl.Nothing terdeteksi sebagai inkonsisten. Ini mengindikasikan kontradiksi fundamental.")
                    print("     Coba periksa individu yang mungkin menjadi anggota owl.Nothing:")
                    problematic_individuals = list(owl.Nothing.instances(world=world))
                    if problematic_individuals:
                        for ind in problematic_individuals:
                            found_related_individual_in_inconsistent_class_check = True
                            print(f"     - Individu {ind.name} adalah anggota dari owl.Nothing!")
                            print(f"       Tipe-tipe dari {ind.name}: {ind.is_a}")
                            print(f"       Properti dari {ind.name}:")
                            for prop, value_list in ind.get_properties().items():
                                for value in value_list if isinstance(value_list, list) else [value_list]:
                                    print(f"         - {prop.name}: {value}")
                    else:
                        print("     - Tidak ada individu yang secara eksplisit diinferensikan sebagai anggota owl.Nothing saat ini (mungkin inkonsistensi TBox murni).")
                    # break # Mungkin tidak perlu break jika ada kelas inkonsisten lain yang ingin diperiksa
                else:
                    print(f"   - Untuk kelas inkonsisten {cls_name}:")
                    related_individuals = list(cls.instances(world=world))
                    if related_individuals:
                        for individual in related_individuals:
                            found_related_individual_in_inconsistent_class_check = True
                            print(f"     - Individu {individual.name} terdaftar sebagai instans dari kelas inkonsisten {cls_name}.")
                    else:
                        print(f"     - Tidak ditemukan individu yang secara langsung merupakan anggota dari {cls_name}.")
            return False

    except owlready2.base.OwlReadyInconsistentOntologyError as e:
        print(f"\n❌ Ontologi TIDAK KONSISTEN SECARA GLOBAL (kemungkinan besar karena ABox/individu): {str(e)}")
        
        print("\n   Mencari individu yang menjadi anggota dari owl.Nothing (indikasi kuat penyebab inkonsistensi ABox):")
        found_problematic_individual_in_error_handling = False # Flag
        if world: # Pastikan world ada
            problematic_individuals = list(owl.Nothing.instances(world=world))
            if problematic_individuals:
                for individual in problematic_individuals:
                    found_problematic_individual_in_error_handling = True
                    print(f"   - Individu BERMASALAH ditemukan: {individual.name} (diinferensikan sebagai anggota owl.Nothing)")
                    print(f"     Tipe-tipe dari {individual.name}: {individual.is_a}")
                    print(f"     Properti dari {individual.name}:")
                    for prop, value_list in individual.get_properties().items():
                        for value in value_list if isinstance(value_list, list) else [value_list]:
                             print(f"       - {prop.name}: {value}")
            
        if not found_problematic_individual_in_error_handling:
            print("   - Tidak ada individu spesifik yang terdeteksi sebagai anggota owl.Nothing secara langsung melalui iterasi standar.")
            print("     Inkonsistensi mungkin lebih kompleks. Pesan error Java di atas mungkin memberikan petunjuk.")
            print("     Coba periksa juga output dari 'inconsistent_classes()' jika ada.")

        if world:
            inconsistent_classes_after_error = list(world.inconsistent_classes())
            if inconsistent_classes_after_error:
                print("\n   Kelas inkonsisten yang juga terdeteksi (mungkin terkait dengan error global):")
                for cls_err in inconsistent_classes_after_error:
                    print(f"   - {cls_err.name if hasattr(cls_err, 'name') else str(cls_err)}")
        return False

    except Exception as e:
        print(f"\n⚠️ Terjadi error lain saat memeriksa konsistensi: {str(e)}")
        import traceback
        traceback.print_exc() 
        print("Pastikan Java Development Kit (JDK) terinstal dan path-nya sudah benar.")
        print("Pastikan juga file ontologi valid dan dapat diakses.")
        return False

def main():
    print("""
===================================================================
  PEMERIKSA KONSISTENSI ONTOLOGI & INDIVIDU (HERMIT/PELLET)
===================================================================
""")

    # --- MODIFIKASI DI SINI ---
    # Path ke file ontologi utama Anda (TBox dan ABox/instans)
    ontology_file_path = r"D:\thesis\Global Ontology\fixed global\GSMFO.owl"  # <--- GANTI PATH ONTOLOGI ANDA

    if not (os.path.exists(ontology_file_path) and os.path.isfile(ontology_file_path) and ontology_file_path.lower().endswith((".owl", ".rdf", ".xml"))):
        print(f"File ontologi tidak ditemukan atau format tidak didukung: {ontology_file_path}")
        return
    
    print(f"\nFile ontologi yang akan diperiksa: {ontology_file_path}")
    
    check_consistency_with_explanation(ontology_file_path)

if __name__ == "__main__":
    # Mengatur path untuk owlready2.JAVA_EXE jika diperlukan.
    # Jika JAVA_HOME dan Path environment variable sudah benar, ini mungkin tidak perlu.
    # Sesuaikan path ini dengan lokasi instalasi JDK Anda.
    default_java_path = r"C:\Program Files\Java\jdk-11\bin\java.exe" # Contoh path
    try:
        # Cek apakah java bisa diakses dari PATH atau JAVA_HOME sudah ada
        java_accessible_via_path = bool(shutil.which("java"))
        java_home_set = bool(os.getenv("JAVA_HOME"))

        if not java_accessible_via_path and not java_home_set:
            if os.path.exists(default_java_path):
                print(f"Info: Mengatur owlready2.JAVA_EXE ke: {default_java_path}")
                owlready2.JAVA_EXE = default_java_path
            else:
                print(f"Peringatan: Java tidak terdeteksi di PATH, JAVA_HOME tidak diatur, dan path default '{default_java_path}' tidak ditemukan.")
                print("Pastikan Java Development Kit (JDK) terinstal dan dapat diakses.")
        elif not java_accessible_via_path and java_home_set:
             print(f"Info: JAVA_HOME diatur ke '{os.getenv('JAVA_HOME')}', namun 'java' tidak ditemukan di PATH. Owlready2 akan mencoba menggunakan JAVA_HOME.")
        else:
            print("Info: Java terdeteksi melalui PATH sistem atau JAVA_HOME.")

    except ImportError:
        # shutil mungkin tidak tersedia di Python < 3.3
        if os.path.exists(default_java_path):
            print(f"Info: Mengatur owlready2.JAVA_EXE ke (shutil tidak tersedia): {default_java_path}")
            owlready2.JAVA_EXE = default_java_path
        else:
            print("Peringatan (shutil tidak tersedia): Pastikan Java terinstal dan dapat diakses. Path default tidak ditemukan.")
    except Exception as e_java_setup:
        print(f"Error saat mencoba konfigurasi Java: {e_java_setup}")

    # Untuk menggunakan Pellet, Anda perlu men-download pellet.jar dan mengatur path-nya.
    # Contoh:
    # pellet_jar_path = r"C:\path\to\your\pellet.jar"
    # if os.path.exists(pellet_jar_path):
    #    owlready2.pellet_path = pellet_jar_path
    #    print(f"Info: Menggunakan Pellet reasoner dari: {pellet_jar_path}")
    # else:
    #    print("Info: Pellet JAR tidak ditemukan di path yang ditentukan. Akan menggunakan HermiT (default).")

    main()
