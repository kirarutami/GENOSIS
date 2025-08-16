import logging
import sys
import os
import json
import argparse # Untuk menangani argumen seperti di command line
import csv
from collections import defaultdict # <-- Impor sudah ada

# ===========================================================
# KONFIGURASI LOGGING (PENTING!)
# ===========================================================
logging.basicConfig(
    level=logging.DEBUG, # Set level ke DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s', # Tambahkan nama file & line number
    force=True,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
print("--- DEBUG: Logging Dikonfigurasi di run_rag_manual.py ---")
sys.stdout.flush()
# ===========================================================

# Impor kelas-kelas yang relevan SEKARANG (setelah logging setup)
print("--- DEBUG: Mulai Impor di run_rag_manual.py ---")
sys.stdout.flush()
try:
    from ontomap.base import BaseConfig
    from ontomap.ontology_matchers.rag.rag import RAG
    from ontomap.ontology_matchers.rag.rag import RAGBasedOpenAILLMArch
    from ontomap.ontology_matchers.retrieval.retrieval import BiEncoderRetrieval
    from ontomap.encoder.rag import (
        IRILabelInRAGEncoder,
        IRILabelChildrensInRAGEncoder,
        IRILabelParentsInRAGEncoder,
        IRILabelDescriptionInRAGEncoder,
        IRILabelParentDescriptionInRAGEncoder,
        IRILabelChildrenDescriptionInRAGEncoder
    )
    from ontomap.utils import io
    print("--- DEBUG: Impor utama BERHASIL ---")
    sys.stdout.flush()
except ImportError as e:
    print(f"--- DEBUG: Gagal melakukan impor krusial: {e} ---")
    logger.exception("Gagal impor, periksa PYTHONPATH atau instalasi.")
    sys.stdout.flush()
    exit()
except Exception as e:
    print(f"--- DEBUG: Error tak terduga saat impor: {e} ---")
    logger.exception("Error tak terduga saat impor.")
    sys.stdout.flush()
    exit()


def load_jsonl(file_path):
    """Fungsi helper sederhana untuk load JSONL."""
    data = []
    if not os.path.exists(file_path):
         logger.error(f"Helper load_jsonl: File tidak ditemukan {file_path}")
         return data
    try:
         with open(file_path, 'r', encoding='utf-8') as f:
              for line in f:
                   try:
                       data.append(json.loads(line.strip()))
                   except json.JSONDecodeError:
                        logger.warning(f"Melewati baris JSON tidak valid di {file_path}: {line.strip()}")
    except Exception as e:
         logger.error(f"Helper load_jsonl: Error membaca {file_path}: {e}", exc_info=True)
         return []
    return data

# ===========================================================
# FUNGSI Filter Kardinalitas (HANYA untuk label 'yes')
# ===========================================================
def apply_cardinality_filter(yes_alignments: list, filter_type: str) -> list:
    """Menerapkan filter kardinalitas HANYA pada hasil alignment 'yes'."""
    # Fungsi ini sekarang HANYA menerima list alignment yang sudah 'yes'
    if not isinstance(yes_alignments, list):
        logger.error(f"Input untuk apply_cardinality_filter bukan list: {type(yes_alignments)}")
        return []
    if not yes_alignments:
        logger.info("Tidak ada alignment 'yes' untuk difilter kardinalitasnya.")
        return []

    logger.info(f"Menerapkan filter kardinalitas '{filter_type}' pada {len(yes_alignments)} alignment 'yes'.")
    print(f"--- DEBUG: Menerapkan filter kardinalitas '{filter_type}' pada {len(yes_alignments)} alignment 'yes' ---")
    sys.stdout.flush()

    # Jika filter 'none', tidak perlu filter kardinalitas, kembalikan 'yes' asli
    if filter_type == "none":
        logger.info("Filter kardinalitas 'none', mengembalikan semua alignment 'yes'.")
        return yes_alignments

    final_alignments = []

    if filter_type == "many-to-one":
        source_groups = defaultdict(list)
        for align in yes_alignments:
             if 'source' in align and 'score' in align:
                  source_groups[align['source']].append(align)
             else:
                  logger.warning(f"Melewati alignment tanpa 'source' atau 'score' untuk filter many-to-one: {align}")
        for source_uri, group in source_groups.items():
            if not group: continue
            if len(group) == 1: final_alignments.append(group[0])
            else:
                try:
                    best_alignment = max(group, key=lambda x: x.get('score', -1.0))
                    final_alignments.append(best_alignment)
                except (TypeError, ValueError) as e: logger.warning(f"Gagal membandingkan skor (m2o) untuk source {source_uri}. Melewati. Error: {e}")

    elif filter_type == "one-to-many":
        target_groups = defaultdict(list)
        for align in yes_alignments:
             if 'target' in align and 'score' in align:
                 target_groups[align['target']].append(align)
             else:
                 logger.warning(f"Melewati alignment tanpa 'target' atau 'score' untuk filter one-to-many: {align}")
        for target_uri, group in target_groups.items():
             if not group: continue
             if len(group) == 1: final_alignments.append(group[0])
             else:
                 try:
                     best_alignment = max(group, key=lambda x: x.get('score', -1.0))
                     final_alignments.append(best_alignment)
                 except (TypeError, ValueError) as e: logger.warning(f"Gagal membandingkan skor (o2m) untuk target {target_uri}. Melewati. Error: {e}")

    elif filter_type == "one-to-one":
        logger.debug("Menerapkan filter one-to-one (many-to-one lalu one-to-many)...")
        m2o_source_groups = defaultdict(list)
        for align in yes_alignments:
            if 'source' in align and 'score' in align: m2o_source_groups[align['source']].append(align)
        many_to_one_filtered = []
        for source_uri, group in m2o_source_groups.items():
            if not group: continue
            if len(group) == 1: many_to_one_filtered.append(group[0])
            else:
                 try: many_to_one_filtered.append(max(group, key=lambda x: x.get('score', -1.0)))
                 except (TypeError, ValueError) as e: logger.warning(f"Gagal membandingkan skor (m2o stage) untuk source {source_uri}. Melewati. Error: {e}")
        o2m_target_groups = defaultdict(list)
        for align in many_to_one_filtered:
             if 'target' in align and 'score' in align: o2m_target_groups[align['target']].append(align)
        final_alignments = []
        for target_uri, group in o2m_target_groups.items():
             if not group: continue
             if len(group) == 1: final_alignments.append(group[0])
             else:
                  try: final_alignments.append(max(group, key=lambda x: x.get('score', -1.0)))
                  except (TypeError, ValueError) as e: logger.warning(f"Gagal membandingkan skor (o2m stage) untuk target {target_uri}. Melewati. Error: {e}")

    else: # Jika filter_type tidak dikenal selain 'none'
        logger.warning(f"Tipe filter kardinalitas tidak dikenal: {filter_type}. Mengembalikan alignment 'yes' asli.")
        final_alignments = yes_alignments

    logger.info(f"Jumlah alignment 'yes' setelah filter {filter_type}: {len(final_alignments)}")
    print(f"--- DEBUG: Jumlah alignment 'yes' setelah filter {filter_type}: {len(final_alignments)} ---")
    sys.stdout.flush()
    return final_alignments
# ===========================================================
# AKHIR FUNGSI BARU
# ===========================================================

# ===========================================================
# Fungsi Utama
# ===========================================================
def main(args):
    logger.info(f"Memulai eksekusi RAG manual dengan args: {args}")
    print(f"--- DEBUG: Masuk fungsi main() ---")
    sys.stdout.flush()

    # 1. Tentukan Kelas Encoder berdasarkan repr
    encoder_map = {
        "C": IRILabelInRAGEncoder,
        "CP": IRILabelParentsInRAGEncoder,
        "CC": IRILabelChildrensInRAGEncoder,
        "CD": IRILabelDescriptionInRAGEncoder,
        "CPD": IRILabelParentDescriptionInRAGEncoder,
        "CCD": IRILabelChildrenDescriptionInRAGEncoder,
    }
    SelectedEncoder = encoder_map.get(args.repr)
    if not SelectedEncoder:
        logger.error(f"Representasi '{args.repr}' tidak valid atau Encoder tidak ditemukan.")
        print(f"--- DEBUG: ERROR - Representasi '{args.repr}' tidak valid ---")
        sys.stdout.flush(); return
    logger.info(f"Menggunakan Encoder: {SelectedEncoder.__name__}")
    print(f"--- DEBUG: Encoder dipilih: {SelectedEncoder.__name__} ---")
    sys.stdout.flush()

    # 2. Siapkan Konfigurasi untuk RAG.__init__
    retriever_config = {
        "class": BiEncoderRetrieval,
        "path": "sentence-transformers/all-mpnet-base-v2",
        "device": args.device,
        "top_k": args.k_retriever
    }
    LLMClass = None
    if "gpt" in args.llm_model_name.lower():
        LLMClass = RAGBasedOpenAILLMArch
    else:
        logger.warning(f"Logika pemilihan kelas LLM lokal belum diimplementasikan untuk {args.llm_model_name}. Menggunakan RAGBasedOpenAILLMArch.")
        LLMClass = RAGBasedOpenAILLMArch

    if not LLMClass:
         logger.error(f"Tidak bisa menentukan kelas LLM untuk model: {args.llm_model_name}")
         print(f"--- DEBUG: ERROR - Tidak bisa tentukan LLM Class ---")
         sys.stdout.flush(); return

    llm_config = {
         "class": LLMClass,
         "model_name": args.llm_model_name,
         "path": args.llm_model_name,
         "device": args.device,
         "temperature": args.temperature,
         "max_token_length": args.max_token_length,
         "sleep": args.sleep,
         "batch_size": args.batch_size,
         "max_prompt_length": args.max_prompt_length
    }
    logger.info(f"Konfigurasi Retriever: {retriever_config}")
    logger.info(f"Konfigurasi LLM: {llm_config}")
    print("--- DEBUG: Konfigurasi Retriever & LLM disiapkan ---")
    sys.stdout.flush()

    # 3. Buat instance RAG
    rag_instance = None
    try:
        print("--- DEBUG: Akan membuat instance RAG ---")
        sys.stdout.flush()
        rag_instance = RAG(
            **{
                "retriever-config": retriever_config,
                "llm-config": llm_config,
            }
        )
        print("--- DEBUG: Instance RAG BERHASIL dibuat ---")
        sys.stdout.flush()
    except Exception as e:
        print(f"--- DEBUG: GAGAL membuat instance RAG: {e} ---")
        logger.error(f"Gagal membuat instance RAG: {e}", exc_info=True)
        sys.stdout.flush(); return

    if rag_instance is None:
        logger.error("Instance RAG tidak berhasil dibuat. Skrip berhenti.")
        print("--- DEBUG: ERROR - Instance RAG None ---")
        sys.stdout.flush(); return

    # 4. Siapkan input_data untuk RAG.generate()
    print("--- DEBUG: Memuat data JSONL untuk RAG generate... ---")
    sys.stdout.flush()
    source_jsonl_path = os.path.join(args.processed_data_path, f"source_{args.repr}.jsonl")
    target_jsonl_path = os.path.join(args.processed_data_path, f"target_{args.repr}.jsonl")
    source_onto_data_list = load_jsonl(source_jsonl_path)
    target_onto_data_list = load_jsonl(target_jsonl_path)

    # SAMPLING
    apply_sampling = False # Set False untuk menjalankan semua data
    num_samples = 1        # Jumlah sampel jika apply_sampling=True
    if apply_sampling and source_onto_data_list:
        print(f"--- DEBUG: Mengambil sampel {num_samples} data sumber pertama ---")
        source_onto_data_list = source_onto_data_list[:num_samples]
        print(f"--- DEBUG: Jumlah data sumber setelah sampling: {len(source_onto_data_list)} ---")
        sys.stdout.flush()
    elif apply_sampling:
         logger.warning("List data sumber kosong, sampling tidak bisa dilakukan.")

    if not source_onto_data_list or not target_onto_data_list:
         logger.error(f"Data source atau target kosong atau gagal dimuat dari {args.processed_data_path} dengan repr={args.repr}. Periksa file JSONL.")
         print("--- DEBUG: ERROR - Gagal load JSONL atau data kosong ---")
         sys.stdout.flush(); return

    source_uri_to_index = {item.get("uri"): i for i, item in enumerate(source_onto_data_list) if item.get("uri")}
    target_uri_to_index = {item.get("uri"): i for i, item in enumerate(target_onto_data_list) if item.get("uri")}
    print("--- DEBUG: Mapping URI ke index dibuat ---")
    sys.stdout.flush()

    task_args = {
         "source": source_onto_data_list,
         "target": target_onto_data_list,
         "task": args.task,
         "repr": args.repr,
    }
    rag_input_dict = {
        "retriever-encoder": SelectedEncoder,
        "llm-encoder": SelectedEncoder.llm_encoder,
        "task-args": task_args,
        "source-onto-uri2index": source_uri_to_index,
        "target-onto-uri2index": target_uri_to_index,
    }
    print("--- DEBUG: Input dictionary untuk RAG.generate() disiapkan ---")
    sys.stdout.flush()

    # 5. Panggil RAG.generate dan proses hasil
    try:
        print("--- DEBUG: Akan memanggil rag_instance.generate() ---")
        sys.stdout.flush()
        results = rag_instance.generate(input_data=rag_input_dict)
        print("--- DEBUG: Pemanggilan rag_instance.generate() SELESAI ---")
        sys.stdout.flush()

        # Dapatkan SEMUA hasil LLM (yes, no, error)
        llm_output_all = results[1].get("llm-output", []) if results and len(results) > 1 and isinstance(results[1], dict) else []
        initial_result_count = len(llm_output_all)
        initial_yes_count = sum(1 for align in llm_output_all if align.get("label") == "yes")
        logger.info(f"Proses RAG generate selesai. Jumlah total hasil LLM: {initial_result_count}. Jumlah awal 'yes': {initial_yes_count}")
        print(f"--- DEBUG: Jumlah total hasil LLM sebelum filter: {initial_result_count}, Jumlah awal 'yes': {initial_yes_count} ---")
        sys.stdout.flush()

        # Pisahkan hasil 'yes' untuk difilter kardinalitasnya
        yes_alignments = [a for a in llm_output_all if a.get("label") == "yes"]
        # Hasil 'no' dan 'error'
        no_error_alignments = [a for a in llm_output_all if a.get("label") != "yes"]

        # TERAPKAN FILTER KARDINALITAS HANYA PADA HASIL 'yes'
        filtered_yes_alignments = apply_cardinality_filter(yes_alignments, args.cardinality_filter)

        # Gabungkan kembali hasil 'yes' yang sudah terfilter dengan hasil 'no' dan 'error'
        final_output_to_save = filtered_yes_alignments + no_error_alignments
        logger.info(f"Jumlah alignment final yang akan disimpan (setelah filter kardinalitas pada 'yes'): {len(final_output_to_save)}")
        print(f"--- DEBUG: Jumlah alignment final untuk disimpan: {len(final_output_to_save)} ---")
        sys.stdout.flush()


        # ===========================================================
        # BAGIAN PENYIMPANAN FILE YANG DIMODIFIKASI (Source, Target, Label)
        # ===========================================================
        # 6. Simpan hasil alignment LLM (yes terfilter + no + error) tanpa skor
        output_subdir = os.path.join(args.output_dir, f"{args.llm_model_name}_{args.repr}_thresh{args.threshold}_card{args.cardinality_filter}")
        os.makedirs(output_subdir, exist_ok=True)
        # Beri nama file yang mencerminkan isinya
        alignment_file = os.path.join(output_subdir, f"llm_alignment_final_{args.cardinality_filter}_label_only.tsv")
        print(f"--- DEBUG: Menyimpan hasil alignment final ({args.cardinality_filter}, tanpa skor) ke: {alignment_file} ---")
        sys.stdout.flush()
        try:
            with open(alignment_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter='\t')
                # Header: Source, Target, Label
                writer.writerow(["Source", "Target", "Label"])
                # Tulis dari final_output_to_save
                for align in final_output_to_save:
                    # Ambil hanya Source, Target, dan Label
                    writer.writerow([align.get("source"), align.get("target"), align.get("label")])
            print(f"--- DEBUG: Selesai menyimpan {len(final_output_to_save)} hasil alignment final (tanpa skor) ---")
            sys.stdout.flush()
        except Exception as e_save:
            print(f"--- DEBUG: GAGAL saat menyimpan hasil final (tanpa skor): {e_save} ---")
            logger.error(f"Error saat menyimpan hasil final (tanpa skor): {e_save}", exc_info=True)
            sys.stdout.flush()
        # ===========================================================
        # AKHIR BAGIAN PENYIMPANAN FILE
        # ===========================================================

    except Exception as e:
        print(f"--- DEBUG: GAGAL saat memanggil rag_instance.generate() atau langkah lainnya: {e} ---")
        logger.error(f"Error saat RAG generate atau langkah lainnya: {e}", exc_info=True)
        sys.stdout.flush()

    print("--- DEBUG: Keluar fungsi main() ---")
    sys.stdout.flush()

# ===========================================================
# Parsing Argumen Command Line
# ===========================================================
if __name__ == "__main__":
    print("--- DEBUG: Skrip run_rag_manual.py dijalankan sebagai main ---")
    sys.stdout.flush()
    parser = argparse.ArgumentParser(description="Manual Runner for LLMs4OM RAG Matching")

    parser.add_argument("--task", type=str, required=True, help="Nama tugas (misal matchOSN_MP)")
    parser.add_argument("--llm_model_name", type=str, required=True, help="Nama model LLM (OpenAI ID atau HF Path)")
    parser.add_argument("--repr", type=str, required=True, choices=["C", "CP", "CC", "CD", "CPD", "CCD"], help="Representasi yang digunakan untuk prompt LLM")
    parser.add_argument("--retriever_output_path", type=str, required=False, help="(Optional) Path ke file candidates.tsv (saat ini tidak digunakan aktif oleh skrip ini)")
    parser.add_argument("--processed_data_path", type=str, required=True, help="Path ke direktori JSONL hasil parsing")
    parser.add_argument("--threshold", type=float, default=0.7, help="Ambang batas skor LLM (saat ini tidak diterapkan aktif oleh skrip ini)")
    parser.add_argument("--cardinality_filter", type=str, default="one-to-one", choices=["one-to-one", "none", "many-to-one", "one-to-many"], help="Filter kardinalitas yang akan diterapkan pada hasil 'yes' (jika bukan 'none')")
    parser.add_argument("--output_dir", type=str, required=True, help="Direktori dasar untuk menyimpan output RAG")

    parser.add_argument("--device", type=str, default="cpu", help="Device (cpu atau cuda)")
    parser.add_argument("--k_retriever", type=int, default=10, help="Nilai K yang digunakan saat retrieval internal")
    parser.add_argument("--temperature", type=float, default=0.7, help="Temperature untuk LLM")
    parser.add_argument("--max_token_length", type=int, default=150, help="Max new tokens untuk LLM (default 100)")
    parser.add_argument("--max_prompt_length", type=int, default=1024, help="Max prompt length untuk tokenizer")
    parser.add_argument("--sleep", type=int, default=5, help="Waktu tidur (detik) antar pemanggilan batch LLM")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size untuk inferensi LLM")

    args = parser.parse_args()

    # Panggil fungsi utama
    main(args)

    print("--- DEBUG: Eksekusi run_rag_manual.py SELESAI ---")
    sys.stdout.flush()