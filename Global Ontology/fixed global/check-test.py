from owlready2 import *
import owlready2
import subprocess

# Atur path file Anda dengan benar
onto = get_ontology(r"D:\thesis\Global Ontology\fixed global\GSMFO.owl").load()

print("Mencoba menjalankan reasoner HermiT...")

try:
    with onto:
        sync_reasoner_hermit()
    
    print("\n✅ Selamat! Ontologi Anda konsisten.")

# 1. Tangkap error spesifik dari proses Java yang gagal
except subprocess.CalledProcessError as e:
    print("\n❌ Error: Ontologi tidak konsisten. HermiT melaporkan kesalahan.")
    print("================ PESAN ERROR DARI HERMIT ================")
    error_message = e.output.decode('utf-8', errors='ignore')
    print(error_message)
    print("=========================================================")

# 2. Tangkap error inkonsistensi spesifik dari Owlready2
except OwlReadyInconsistentOntologyError as e:
    print("\n❌ Error: Owlready2 melaporkan 'OwlReadyInconsistentOntologyError'.")
    print("Ini mengonfirmasi bahwa ontologi Anda tidak konsisten secara logika.")
    print("Gunakan Protégé untuk menemukan penjelasan detail mengenai axiom yang bertentangan.")
    
    # Mencoba lagi untuk mencetak kelas yang tidak konsisten
    inconsistent_classes = list(default_world.inconsistent_classes())
    if inconsistent_classes:
        print("\nKelas-kelas berikut terdeteksi tidak konsisten (menjadi subclass dari owl.Nothing):")
        for cls in inconsistent_classes:
            print(f"- {cls.name}")

# 3. Tangkap SEMUA error lain yang mungkin terjadi
except Exception as e:
    print("\n❌ Terjadi error yang tidak terduga. Berikut detailnya:")
    print(f"   Tipe Error      : {type(e)}")
    print(f"   Argumen Error   : {e.args}")
    print(f"   Representasi    : {repr(e)}")
    print("\nSilakan bagikan detail di atas.")