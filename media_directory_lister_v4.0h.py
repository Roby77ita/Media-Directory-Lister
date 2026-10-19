import time

_AVVIO = time.perf_counter()  # serve a misurare quanto impiega ad aprirsi la finestra (avvio.log)

import copy
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import traceback
import webbrowser
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
except ImportError:  # Python senza tkinter: lo spieghiamo invece di far chiudere la console di colpo
    print("ERRORE / ERROR: questo Python non include tkinter (l'interfaccia grafica) / "
          "this Python does not include tkinter.\n"
          "Reinstalla Python da python.org lasciando attiva l'opzione 'tcl/tk and IDLE'.")
    if sys.stdin and sys.stdin.isatty():
        input("\nPremi Invio per chiudere... / Press Enter to close...")
    sys.exit(1)

VERSIONE = "4.0h"
AUTORE = "Roby77"
URL_FFMPEG = "https://ffmpeg.org/download.html"  # dove scaricare FFmpeg (include ffprobe)
EMAIL_CONTATTI = "roby77dopa@gmail.com"  # per suggerimenti e segnalazioni (finestra del pulsante «?»)
MAX_RECENTI = 10  # quante cartelle scansionate ricordare nel menu a tendina
# file ignorati: non compaiono nel report né nei totali
ESTENSIONI_ESCLUSE = {"ini", "log", "txt", "jpg", "m3u", "png", "info", "pdf", "cue", "nfo", "m3u8", "sfv", "md5", "accurip", "jpeg", "toc", "avif"}  # per estensione (maiuscole/minuscole indifferenti)
NOMI_ESCLUSI = {"thumbs.db", "folder.jpg", "cover.jpg"}  # per nome completo del file
IS_WIN = sys.platform == "win32"

# ffprobe viene lanciato solo sui file con queste estensioni (evita chiamate inutili su .txt, .jpg, ecc.)
ESTENSIONI_MEDIA = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "mpg", "mpeg", "ts", "m2ts", "3gp",
    "mp3", "flac", "wav", "aac", "m4a", "ogg", "opus", "wma", "aiff", "ac3", "mka",
}


# id di tutte le colonne disponibili nel report (i titoli sono nelle traduzioni: "col_<id>")
COLONNE = ["nome", "artista", "album", "titolo", "anno", "traccia", "tipo", "est", "dim", "data", "durata",
           "ris", "colore", "hdr", "dv", "fps", "cv", "ca", "canali", "formato", "qualita", "copertina", "tracce",
           "bitrate"]

# come si raggruppano le caselle delle colonne nella finestra (chiave del titolo del gruppo, colonne in ordine di
# visualizzazione, 3 per riga). Vale solo per la finestra: nel report le colonne escono nell'ordine di COLONNE.
# Una colonna nuova non elencata qui compare comunque, in coda al primo gruppo.
GRUPPI_COLONNE = [
    ("gr_file", ["nome", "tipo", "est", "dim", "data", "durata", "bitrate"]),
    ("gr_tag", ["artista", "album", "titolo", "anno", "traccia", "copertina"]),
    ("gr_video", ["ris", "fps", "cv", "colore", "hdr", "dv"]),
    ("gr_audio", ["ca", "formato", "canali", "tracce", "qualita"]),
]

LAYOUT = ("verticale", "orizzontale")  # disposizione della finestra del programma (menù in alto)


# ---------------------------------------------------------------- traduzioni
# Per aggiungere una lingua: copia il blocco "it", traduci i valori e aggiungila anche a LINGUE.
# Prefissi: col_/th_ = titoli delle colonne (finestra / intestazioni del report), r_ = testi fissi del
# report HTML, j_ = testi usati dal JavaScript del report, tutto il resto = finestra del programma.

LINGUE = {"it": "Italiano", "en": "English"}

TESTI = {
    "it": {
        "sottotitolo": "Versione {v}  ·  report HTML con i metadati dei file audio e video",
        "cartella_titolo": "Cartella multimediale",
        "sfoglia": "Sfoglia...",
        "nota_recenti": "Nel menu a tendina trovi le ultime cartelle scansionate.",
        "mostra_come": "Nel report mostra la cartella come:",
        "percorso_completo": "Nome e percorso",
        "solo_nome": "Solo nome",
        "usa_cache": "Usa la cache (rianalizza solo i file nuovi o modificati)",
        "svuota_cache": "Svuota cache", "usa_cache_breve": "Usa la cache",
        "svuota_cronologia": "Svuota cronologia", "cronologia_titolo": "Cronologia sorgenti",
        "cronologia_conferma": "Svuotare l'elenco delle cartelle recenti del menu a tendina?\n\nLa cartella scritta ora nella casella e quelle salvate nei profili non cambiano.",
        "cronologia_svuotata": "Cronologia delle cartelle svuotata.",
        "colonne_titolo": "Colonne del report",
        "gr_file": "File", "gr_tag": "Tag musicali", "gr_video": "Video", "gr_audio": "Audio",
        "layout_verticale": "Layout verticale", "layout_orizzontale": "Layout orizzontale",
        "aspetto_menu": "Aspetto", "tema_scuro": "Tema scuro", "tema_chiaro": "Tema chiaro",
        "tutte": "Tutte",
        "nessuna": "Nessuna",
        "attesa": "In attesa...",
        "genera": "Genera report HTML",
        "annulla": "Annulla",
        "versione_ff": "versione {v}",
        "versione_nd": "versione non rilevata",
        "percorso_ff": "Percorso: {p}",
        "ffprobe_mancante": "ERRORE: ffprobe non trovato! Mettilo nella cartella del programma o nel PATH.",
        "errore": "Errore",
        "info": "Info",
        "cartella_non_valida": "Seleziona una cartella valida!",
        "nessuna_colonna": "Seleziona almeno una colonna!",
        "salva_titolo": "Salva report",
        "ricerca_file": "Ricerca dei file...",
        "ricerca_file_n": "Ricerca dei file... {n} trovati",
        "analisi": "Analisi: {n}/{totale} ({pct}%)",
        "analisi_stima": "Analisi: {n}/{totale} ({pct}%) · circa {tempo} rimasti",
        "cartella_vuota": "Cartella vuota.",
        "annullata": "Operazione annullata.",
        "salvataggio_fallito": "Impossibile salvare il report:\n{errore}",
        "errore_imprevisto": "Errore imprevisto:\n{errore}",
        "report_salvato": "Report HTML salvato!",
        "dettaglio_cache": "  ·  dalla cache: {h}, analizzati: {a}",
        "completato_aperto": "Completato! Report aperto nel browser.",
        "completato_salvato": "Completato! Report salvato.",
        "salvato_titolo": "Report salvato",
        "apertura_fallita": "Non è stato possibile aprirlo automaticamente.\n\n{percorso}",
        "cache_titolo": "Cache",
        "cache_svuotata": "Cache svuotata: la prossima scansione analizzerà di nuovo tutti i file.",
        "cache_gia_vuota": "La cache è già vuota.",
        "cache_errore": "Impossibile svuotare la cache:\n{errore}",
        "scarica_ffmpeg": "Scarica FFmpeg (include ffprobe): {url}",
        "tipo_etichetta": "Tipo:", "tipo_generale": "Generale", "tipo_musica": "Musica", "tipo_film": "Film",
        "tipo_titolo": "Tipo di profilo",
        "tipo_testo": "Il profilo diventa di tipo «{tipo}».\n\nVuoi anche impostare le colonne predefinite di questo tipo? Le colonne attuali del profilo verranno sostituite.",
        "profilo_nota": "Cartella, tipo, colonne, esclusioni e opzioni si ricordano per ogni profilo.",
        "profilo_etichetta": "Profilo:", "profilo_gestisci": "Gestisci", "profilo_nuovo": "Nuovo profilo...",
        "profilo_rinomina": "Rinomina profilo...", "profilo_elimina": "Elimina profilo",
        "escl_bottone": "Esclusioni ({n})...",
        "nuovo_titolo": "Nuovo profilo", "nuovo_testo": "Nome del nuovo profilo (parte da una copia di «{nome}»):",
        "nuovo_nome": "Nome del profilo (per esempio Animazione):", "nuovo_tipo": "Tipo:",
        "nuovo_modello": "Parti dalle colonne predefinite del tipo (altrimenti copia quelle attuali)",
        "nuovo_nota": "Cartella, esclusioni e opzioni attuali vengono copiate nel nuovo profilo: dopo la creazione scegli la sua cartella e premi Salva.",
        "elimina_ultimo_testo": "«{nome}» è l'ultimo profilo.\n\nEliminandolo ne viene creato uno nuovo, «Generale», con le impostazioni predefinite (tutte le colonne, esclusioni predefinite). La casella della cartella resta com'è. Continuare?",
        "nuovo_crea": "Crea profilo", "profilo_salvato_breve": "✓ Salvato", "profilo_modifica": "Modifica profilo...", "modifica_titolo": "Modifica profilo", "modifica_nome": "Nome del profilo:", "modifica_cartella": "Cartella sorgente del profilo:", "profilo_salva": "Salva", "profilo_salvato": "Profilo «{nome}» salvato.",
        "rinomina_titolo": "Rinomina profilo", "rinomina_testo": "Nuovo nome per «{nome}»:",
        "elimina_titolo": "Elimina profilo", "elimina_testo": "Eliminare il profilo «{nome}»?",
        "profilo_ultimo": "Deve restare almeno un profilo.",
        "nome_vuoto": "Scrivi un nome per il profilo.", "nome_esiste": "Esiste già un profilo chiamato «{nome}».",
        "nome_lungo": "Il nome è troppo lungo (massimo 40 caratteri).",
        "escl_titolo": "Esclusioni del profilo «{nome}»", "escl_estensioni": "Estensioni escluse",
        "escl_estensioni_nota": "Separate da spazi, virgole o a capo; il punto è facoltativo (txt oppure .txt). Maiuscole e minuscole sono uguali.",
        "escl_nomi": "Nomi di file esclusi", "escl_nomi_nota": "Un nome completo per riga, per esempio thumbs.db o folder.jpg.",
        "escl_ripristina": "Ripristina predefinite", "escl_salva": "Salva",
        "escl_ignorate": "Voci ignorate perché non valide: {voci}",
        "contatti_titolo": "Suggerimenti e contatti",
        "contatti_testo": "Hai suggerimenti, idee per migliorare il programma, richieste di modifica oppure vuoi segnalare un problema tecnico?",
        "contatti_email_intro": "Per contattarmi via email:",
        "chiudi": "Chiudi",
        "tempi": "  ·  tempi: elenco file {a} s, analisi {b} s, report {c} s",
        "errore_fatale": "Si è verificato un errore:\n{errore}\n\nI dettagli sono stati salvati in:\n{log}",
        "dividi_sottocartelle": "Dividi il report per sottocartelle",
        # titoli delle colonne (finestra) e, se diversi, delle intestazioni del report
        "col_nome": "Nome file", "col_tipo": "Tipo", "col_est": "Estensione", "col_dim": "Dimensione",
        "col_durata": "Durata", "col_ris": "Risoluzione", "col_colore": "Profondità di colore", "col_hdr": "HDR", "col_dv": "Dolby Vision",
        "col_fps": "FPS", "col_cv": "Codec video", "col_ca": "Codec audio", "col_canali": "Canali audio",
        "col_formato": "Formato audio", "col_tracce": "Tracce audio", "col_bitrate": "Bitrate",
        "th_est": "Est.", "th_colore": "Prof. colore", "th_cv": "Codec V", "th_ca": "Codec A",
        "col_artista": "Artista", "col_album": "Album", "col_titolo": "Titolo", "col_anno": "Anno",
        "col_traccia": "Numero traccia", "col_data": "Data modifica", "col_qualita": "Qualità (lossless/lossy)",
        "col_copertina": "Copertina incorporata", "th_traccia": "N.", "th_data": "Modificato",
        "th_qualita": "Qualità", "th_copertina": "Copertina",
        # report HTML
        "r_cartella": "Cartella:", "r_generato": "Generato il:",
        "r_formato_data": "%d/%m/%Y alle %H:%M:%S", "r_totali": "File totali:", "r_n_cartelle": "Cartelle:", "r_spazio": "Spazio occupato:",
        "r_sep_migliaia": ".", "r_cerca": "Cerca file...", "r_tutti": "Tutti", "r_video": "Video",
        "r_audio": "Audio", "r_solo_hdr": "Solo HDR", "r_res_qualsiasi": "Qualsiasi risoluzione",
        "r_res_720": "Sotto 720p (SD)", "r_res_1080": "Sotto 1080p (HD)", "r_res_1440": "Sotto 1440p",
        "r_res_4k": "Sotto 4K", "r_azzera": "Azzera filtri", "r_unica": "Pagina unica", "r_stampa": "Stampa", "r_tema": "Tema", "r_per_pagina": "per pagina", "r_gruppi": "Dividi per sottocartelle", "r_prec": "Precedente", "r_succ": "Successiva",
        "r_data_qualsiasi": "Qualsiasi data di modifica", "r_data_7": "Modificati negli ultimi 7 giorni",
        "r_data_30": "Modificati negli ultimi 30 giorni", "r_csv": "Esporta CSV", "r_colonne": "Colonne", "r_riepilogo": "Riepilogo",
        # JavaScript del report
        "j_pagina": "Pagina", "j_tema_chiaro": "Tema chiaro", "j_tema_scuro": "Tema scuro", "j_filtri": "Filtri attivi",
        "j_conferma_stampa": "Stampare {n} file può richiedere moltissime pagine e rendere lento il browser. Continuare?", "j_pagina_unica": "Tutti i file in un'unica pagina",
        "j_conferma": "Mostrare {n} file in un'unica pagina può rendere il browser molto lento. Continuare?", "j_di": "di", "j_mostrati": "file mostrati", "j_su": "su",
        "j_radice": "(cartella principale)", "j_file": "file", "j_si": "Sì", "j_no": "No", "j_profilo": "Profilo", "j_con_el": "(con EL)",
        "j_tipo_video": "Video", "j_tipo_audio": "Audio", "j_tipo_generico": "Generico",
        "j_fmt_data": "dmy", "j_csv_sep": ";", "j_cartella": "Cartella",
        "j_riep_titolo": "Riepilogo", "j_riep_ore": "ore", "j_riep_artisti": "artisti", "j_riep_album": "album",
        "j_riep_altro": "Altro", "j_riep_altri": "Altri", "j_riep_sdr": "Senza HDR", "j_riep_hdr_altro": "HDR (altro)",
        "j_riep_video": "video", "j_riep_brani": "brani",
        "j_col_tutte": "Tutte", "j_col_predef": "Predefinite", "j_gr_file": "File", "j_gr_tag": "Tag musicali",
        "j_gr_video": "Video", "j_gr_audio": "Audio",
    },
    "en": {
        "sottotitolo": "Version {v}  ·  HTML report with the metadata of your audio and video files",
        "cartella_titolo": "Media folder",
        "sfoglia": "Browse...",
        "nota_recenti": "The drop-down menu lists the folders you scanned most recently.",
        "mostra_come": "Show the folder in the report as:",
        "percorso_completo": "Name and path",
        "solo_nome": "Name only",
        "usa_cache": "Use the cache (re-analyze only new or modified files)",
        "svuota_cache": "Clear cache", "usa_cache_breve": "Use the cache",
        "svuota_cronologia": "Clear history", "cronologia_titolo": "Source history",
        "cronologia_conferma": "Clear the list of recent folders in the drop-down menu?\n\nThe folder currently in the box and the ones saved in profiles are not changed.",
        "cronologia_svuotata": "Folder history cleared.",
        "colonne_titolo": "Report columns",
        "gr_file": "File", "gr_tag": "Music tags", "gr_video": "Video", "gr_audio": "Audio",
        "layout_verticale": "Vertical layout", "layout_orizzontale": "Horizontal layout",
        "aspetto_menu": "Appearance", "tema_scuro": "Dark theme", "tema_chiaro": "Light theme",
        "tutte": "All",
        "nessuna": "None",
        "attesa": "Waiting...",
        "genera": "Generate HTML report",
        "annulla": "Cancel",
        "versione_ff": "version {v}",
        "versione_nd": "version not detected",
        "percorso_ff": "Path: {p}",
        "ffprobe_mancante": "ERROR: ffprobe not found! Put it in the program folder or in the PATH.",
        "errore": "Error",
        "info": "Info",
        "cartella_non_valida": "Select a valid folder!",
        "nessuna_colonna": "Select at least one column!",
        "salva_titolo": "Save report",
        "ricerca_file": "Searching for files...",
        "ricerca_file_n": "Searching for files... {n} found",
        "analisi": "Analyzing: {n}/{totale} ({pct}%)",
        "analisi_stima": "Analyzing: {n}/{totale} ({pct}%) · about {tempo} left",
        "cartella_vuota": "Empty folder.",
        "annullata": "Operation cancelled.",
        "salvataggio_fallito": "Could not save the report:\n{errore}",
        "errore_imprevisto": "Unexpected error:\n{errore}",
        "report_salvato": "HTML report saved!",
        "dettaglio_cache": "  ·  from cache: {h}, analyzed: {a}",
        "completato_aperto": "Done! Report opened in the browser.",
        "completato_salvato": "Done! Report saved.",
        "salvato_titolo": "Report saved",
        "apertura_fallita": "It could not be opened automatically.\n\n{percorso}",
        "cache_titolo": "Cache",
        "cache_svuotata": "Cache cleared: the next scan will analyze all files again.",
        "cache_gia_vuota": "The cache is already empty.",
        "cache_errore": "Could not clear the cache:\n{errore}",
        "scarica_ffmpeg": "Download FFmpeg (includes ffprobe): {url}",
        "tipo_etichetta": "Type:", "tipo_generale": "General", "tipo_musica": "Music", "tipo_film": "Movies",
        "tipo_titolo": "Profile type",
        "tipo_testo": "The profile becomes type \"{tipo}\".\n\nDo you also want to set the default columns for this type? The profile's current columns will be replaced.",
        "profilo_nota": "Folder, type, columns, exclusions and options are remembered for each profile.",
        "profilo_etichetta": "Profile:", "profilo_gestisci": "Manage", "profilo_nuovo": "New profile...",
        "profilo_rinomina": "Rename profile...", "profilo_elimina": "Delete profile",
        "escl_bottone": "Exclusions ({n})...",
        "nuovo_titolo": "New profile", "nuovo_testo": "Name of the new profile (starts as a copy of «{nome}»):",
        "nuovo_nome": "Profile name (for example Animation):", "nuovo_tipo": "Type:",
        "nuovo_modello": "Start from the default columns of the type (otherwise copy the current ones)",
        "nuovo_nota": "The current folder, exclusions and options are copied into the new profile: after creating it, choose its folder and press Save.",
        "elimina_ultimo_testo": "\"{nome}\" is the last profile.\n\nDeleting it creates a new one, \"Generale\", with the default settings (all columns, default exclusions). The folder box stays as it is. Continue?",
        "nuovo_crea": "Create profile", "profilo_salvato_breve": "✓ Saved", "profilo_modifica": "Edit profile...", "modifica_titolo": "Edit profile", "modifica_nome": "Profile name:", "modifica_cartella": "Profile source folder:", "profilo_salva": "Save", "profilo_salvato": "Profile «{nome}» saved.",
        "rinomina_titolo": "Rename profile", "rinomina_testo": "New name for «{nome}»:",
        "elimina_titolo": "Delete profile", "elimina_testo": "Delete the profile «{nome}»?",
        "profilo_ultimo": "At least one profile must remain.",
        "nome_vuoto": "Enter a name for the profile.", "nome_esiste": "A profile named «{nome}» already exists.",
        "nome_lungo": "The name is too long (40 characters maximum).",
        "escl_titolo": "Exclusions for profile «{nome}»", "escl_estensioni": "Excluded extensions",
        "escl_estensioni_nota": "Separated by spaces, commas or new lines; the dot is optional (txt or .txt). Case does not matter.",
        "escl_nomi": "Excluded file names", "escl_nomi_nota": "One full name per line, for example thumbs.db or folder.jpg.",
        "escl_ripristina": "Restore defaults", "escl_salva": "Save",
        "escl_ignorate": "Entries ignored as invalid: {voci}",
        "contatti_titolo": "Feedback and contact",
        "contatti_testo": "Do you have suggestions, ideas to improve the program, change requests, or do you want to report a technical problem?",
        "contatti_email_intro": "To contact me by email:",
        "chiudi": "Close",
        "tempi": "  ·  times: file listing {a} s, analysis {b} s, report {c} s",
        "errore_fatale": "An error occurred:\n{errore}\n\nDetails were saved to:\n{log}",
        "dividi_sottocartelle": "Group the report by subfolder",
        "col_nome": "File name", "col_tipo": "Type", "col_est": "Extension", "col_dim": "Size",
        "col_durata": "Duration", "col_ris": "Resolution", "col_colore": "Color depth", "col_hdr": "HDR", "col_dv": "Dolby Vision",
        "col_fps": "FPS", "col_cv": "Video codec", "col_ca": "Audio codec", "col_canali": "Audio channels",
        "col_formato": "Audio format", "col_tracce": "Audio tracks", "col_bitrate": "Bitrate",
        "th_est": "Ext.", "th_colore": "Color depth",
        "col_artista": "Artist", "col_album": "Album", "col_titolo": "Title", "col_anno": "Year",
        "col_traccia": "Track number", "col_data": "Modified date", "col_qualita": "Quality (lossless/lossy)",
        "col_copertina": "Embedded cover art", "th_traccia": "No.", "th_data": "Modified",
        "th_qualita": "Quality", "th_copertina": "Cover",
        "r_cartella": "Folder:", "r_generato": "Generated on:",
        "r_formato_data": "%Y-%m-%d %H:%M:%S", "r_totali": "Total files:", "r_n_cartelle": "Folders:", "r_spazio": "Space used:",
        "r_sep_migliaia": ",", "r_cerca": "Search files...", "r_tutti": "All", "r_video": "Video",
        "r_audio": "Audio", "r_solo_hdr": "HDR only", "r_res_qualsiasi": "Any resolution",
        "r_res_720": "Below 720p (SD)", "r_res_1080": "Below 1080p (HD)", "r_res_1440": "Below 1440p",
        "r_res_4k": "Below 4K", "r_azzera": "Reset filters", "r_unica": "Single page", "r_stampa": "Print", "r_tema": "Theme", "r_per_pagina": "per page", "r_gruppi": "Group by subfolder", "r_prec": "Previous", "r_succ": "Next",
        "r_data_qualsiasi": "Any modified date", "r_data_7": "Modified in the last 7 days",
        "r_data_30": "Modified in the last 30 days", "r_csv": "Export CSV", "r_colonne": "Columns", "r_riepilogo": "Summary",
        "j_pagina": "Page", "j_tema_chiaro": "Light theme", "j_tema_scuro": "Dark theme", "j_filtri": "Active filters",
        "j_conferma_stampa": "Printing {n} files may take a great many pages and make the browser very slow. Continue?", "j_pagina_unica": "All files on a single page",
        "j_conferma": "Showing {n} files on a single page may make the browser very slow. Continue?", "j_di": "of", "j_mostrati": "files shown", "j_su": "of",
        "j_radice": "(root folder)", "j_file": "files", "j_si": "Yes", "j_no": "No", "j_profilo": "Profile", "j_con_el": "(with EL)",
        "j_tipo_video": "Video", "j_tipo_audio": "Audio", "j_tipo_generico": "Generic",
        "j_fmt_data": "ymd", "j_csv_sep": ",", "j_cartella": "Folder",
        "j_riep_titolo": "Summary", "j_riep_ore": "hours", "j_riep_artisti": "artists", "j_riep_album": "albums",
        "j_riep_altro": "Other", "j_riep_altri": "Others", "j_riep_sdr": "No HDR", "j_riep_hdr_altro": "HDR (other)",
        "j_riep_video": "video", "j_riep_brani": "tracks",
        "j_col_tutte": "All", "j_col_predef": "Default", "j_gr_file": "File", "j_gr_tag": "Music tags",
        "j_gr_video": "Video", "j_gr_audio": "Audio",
    },
}


def traduci(lingua, chiave, **valori):
    """Testo nella lingua scelta (se manca, ricade sull'italiano); i {segnaposto} si riempiono con `valori`."""
    testo = TESTI.get(lingua, TESTI["it"]).get(chiave)
    if testo is None:
        testo = TESTI["it"][chiave]
    return testo.format(**valori) if valori else testo


# ---------------------------------------------------------------- tempi di avvio

FASI_AVVIO = []


def segna_fase(nome):
    """Registra (e scrive sulla console) a che punto è l'avvio: se si blocca, l'ultima riga dice dove."""
    secondi = time.perf_counter() - _AVVIO
    FASI_AVVIO.append((nome, secondi))
    print(f"[avvio {secondi:6.2f} s] {nome}", file=sys.stderr, flush=True)


def salva_log_avvio():
    """Scrive avvio.log (accanto a config.json) con i tempi di ogni fase dell'ultima apertura."""
    try:
        percorso = os.path.join(os.path.dirname(percorso_config()), "avvio.log")
        os.makedirs(os.path.dirname(percorso), exist_ok=True)
        with open(percorso, "w", encoding="utf-8") as f:
            f.write(f"Media Directory Lister v{VERSIONE} - tempi di avvio (secondi dall'inizio, e durata di ogni fase)\n")
            precedente = 0.0
            for nome, secondi in list(FASI_AVVIO):
                f.write(f"{secondi:7.2f}  (+{secondi - precedente:5.2f})  {nome}\n")
                precedente = secondi
    except OSError:
        pass


# ---------------------------------------------------------------- ffprobe

def trova_ffprobe():
    """Cerca ffprobe prima accanto al programma (un solo controllo, istantaneo) e solo dopo nel PATH:
    scorrere il PATH può essere lentissimo se contiene dischi di rete spenti o irraggiungibili."""
    nome = "ffprobe.exe" if IS_WIN else "ffprobe"
    if getattr(sys, "frozen", False):
        cartelle = [os.path.dirname(sys.executable), getattr(sys, "_MEIPASS", "")]
    else:
        cartelle = [os.path.dirname(os.path.abspath(__file__))]
    for c in cartelle:
        locale = os.path.join(c, nome)
        if c and os.path.exists(locale):
            return locale
    return shutil.which("ffprobe")


def _opzioni_senza_finestra():
    """Su Windows evita che compaia una finestra nera a ogni chiamata di ffprobe."""
    if not IS_WIN:
        return {}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {"startupinfo": si, "creationflags": subprocess.CREATE_NO_WINDOW}


def versione_ffprobe(ffprobe):
    """Versione di ffprobe (es. '7.1-essentials_build-www.gyan.dev'), oppure None se non rilevabile."""
    if not ffprobe:
        return None
    try:
        r = subprocess.run([ffprobe, "-version"], capture_output=True, text=True, encoding="utf-8",
                           errors="ignore", timeout=10, **_opzioni_senza_finestra())
    except (OSError, subprocess.SubprocessError):
        return None
    righe = r.stdout.splitlines()
    parti = righe[0].split() if righe else []
    return parti[2] if len(parti) >= 3 and parti[1] == "version" else None


def a_capo(testo, righe=3, minimo=50):
    """Spezza un testo lungo (senza spazi, come un percorso) in al massimo `righe` righe, preferendo i separatori."""
    if len(testo) <= minimo:
        return testo
    n = max(minimo, -(-len(testo) // righe) + 10)  # lunghezza di riga: tre righe bastano sempre a coprire il testo
    out = []
    while len(testo) > n and len(out) < righe - 1:
        taglio = n
        for i in range(n, n - 11, -1):  # cerca un separatore poco prima del limite
            if testo[i - 1] in "\\/":
                taglio = i
                break
        out.append(testo[:taglio])
        testo = testo[taglio:]
    out.append(testo)
    return "\n".join(out)


def esegui_ffprobe(ffprobe, percorso):
    extra = _opzioni_senza_finestra()
    r = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", percorso],
        capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=30, **extra,
    )
    return json.loads(r.stdout) if r.stdout.strip() else {}


def _numero(valore):
    try:
        return float(valore)
    except (TypeError, ValueError):
        return None


def _fps(valore):
    try:
        n, d = (valore or "0/0").split("/")
        return round(float(n) / float(d), 2) if float(d) else None
    except ValueError:
        return None


def _is_hdr(video):
    """HDR10/HLG (curva di trasferimento PQ o HLG) oppure Dolby Vision (side data)."""
    if video.get("color_transfer") in ("smpte2084", "arib-std-b67"):
        return True
    for sd in video.get("side_data_list", []):
        tipo = str(sd.get("side_data_type", "")).upper()
        if "DOVI" in tipo or "DOLBY VISION" in tipo or sd.get("dv_profile") is not None:
            return True
    return False


def elenca_file(cartella, statistiche=None, estensioni=None, nomi=None, annulla=None, avanzamento=None):
    """Elenco ordinato [(percorso, dimensione, data_modifica_ns)] di tutti i file, esclusi quelli con le estensioni
    in `estensioni` o i nomi in `nomi` (insiemi in minuscolo; se mancano valgono ESTENSIONI_ESCLUSE e NOMI_ESCLUSI).

    Usa os.scandir: la dimensione arriva insieme all'elenco della cartella (su Windows senza altri accessi
    al disco), invece di una chiamata a getsize() per ogni file. L'ordine (cartella, nome) è calcolato
    una volta sola qui, così il report esce già ordinato.
    Se si passa un dizionario come `statistiche`, vi si scrive "cartelle": il numero di sottocartelle
    attraversate (quella di partenza esclusa), anche se vuote o con soli file esclusi.
    `annulla` (threading.Event): se viene impostato la ricerca si ferma e la funzione restituisce None.
    `avanzamento(n)`: chiamata ogni tanto (al massimo 5 volte al secondo) con il numero di file trovati finora."""
    estensioni = ESTENSIONI_ESCLUSE if estensioni is None else estensioni
    nomi = NOMI_ESCLUSI if nomi is None else nomi
    trovati, da_visitare, n_cartelle = [], [cartella], 0
    visti, ultimo = 0, time.perf_counter()
    while da_visitare:
        if annulla is not None and annulla.is_set():
            return None
        try:
            with os.scandir(da_visitare.pop()) as voci:
                for v in voci:
                    visti += 1
                    if visti % 64 == 0:  # ogni tanto: controlla l'annullamento e aggiorna il conteggio
                        if annulla is not None and annulla.is_set():
                            return None
                        adesso = time.perf_counter()
                        if avanzamento is not None and adesso - ultimo >= 0.2:
                            avanzamento(len(trovati))
                            ultimo = adesso
                    try:
                        if v.is_dir(follow_symlinks=False):
                            da_visitare.append(v.path)
                            n_cartelle += 1
                            continue
                        if not v.is_file():
                            continue
                    except OSError:
                        continue  # voce illeggibile: la salta
                    nome = v.name.lower()
                    if nome in nomi or os.path.splitext(nome)[1].lstrip(".") in estensioni:
                        continue
                    try:
                        info = v.stat()
                        dimensione, modifica = info.st_size, info.st_mtime_ns
                    except OSError:
                        dimensione, modifica = 0, None
                    trovati.append((v.path, dimensione, modifica))
        except OSError:
            continue  # cartella non accessibile
    trovati.sort(key=lambda t: (os.path.dirname(t[0]).lower(), os.path.basename(t[0]).lower()))
    if statistiche is not None:
        statistiche["cartelle"] = n_cartelle
    return trovati


def _imposta(rec, **valori):
    """Aggiunge al record solo i valori presenti: meno memoria e un report più leggero."""
    rec.update({k: v for k, v in valori.items() if v is not None and v != ""})


def _tipo_hdr(video):
    """Tipo di HDR dalla curva di trasferimento: PQ = HDR10 (e compatibili), HLG = broadcast."""
    t = video.get("color_transfer")
    return "HDR10" if t == "smpte2084" else ("HLG" if t == "arib-std-b67" else None)


def _rapporto(v):
    """ffprobe scrive molti valori come frazione («10000000/10000»)."""
    try:
        if isinstance(v, str) and "/" in v:
            n, d = v.split("/")
            return float(n) / float(d) if float(d) else None
        return float(v)
    except (TypeError, ValueError):
        return None


def _luminanza_hdr(video):
    """(picco di luminanza del master in nit, MaxCLL, MaxFALL) dai metadati statici, quando ci sono."""
    mx = mc = mf = None
    for sd in video.get("side_data_list", []):
        tipo = str(sd.get("side_data_type", "")).lower()
        if "mastering display" in tipo:
            mx = _rapporto(sd.get("max_luminance"))
        elif "content light level" in tipo:
            mc, mf = _numero(sd.get("max_content")), _numero(sd.get("max_average"))
    intero = lambda x: int(round(x)) if x and x > 0 else None
    return intero(mx), intero(mc), intero(mf)


_NOMI_CODEC_AUDIO = {"aac": "AAC", "flac": "FLAC", "opus": "Opus", "mp3": "MP3", "mp2": "MP2", "vorbis": "Vorbis",
                     "alac": "ALAC", "ac3": "AC3", "eac3": "E-AC3", "truehd": "TrueHD", "wavpack": "WavPack"}


def _codec_audio(stream):
    """Nome abituale del codec audio; per DTS e Dolby si guarda il profilo (DTS-HD MA, DTS:X, Atmos...)."""
    nome = str(stream.get("codec_name") or "").lower()
    profilo = str(stream.get("profile") or "").lower()
    if nome == "dts":
        if "dts:x" in profilo:
            return "DTS:X"
        return "DTS-HD MA" if "dts-hd ma" in profilo else ("DTS-HD HRA" if "dts-hd hra" in profilo else "DTS")
    base = "PCM" if nome.startswith("pcm") else _NOMI_CODEC_AUDIO.get(nome, nome.upper())
    return base + " Atmos" if "atmos" in profilo and nome in ("truehd", "eac3") else base


def _canali_testo(stream):
    """Canali nella notazione abituale: 2.0, 5.1, 7.1, 7.1.4..."""
    layout = str(stream.get("channel_layout") or "")
    m = re.match(r"(\d+\.\d+(?:\.\d+)?)", layout)
    if m:
        return m.group(1)
    if layout in ("stereo", "mono"):
        return "2.0" if layout == "stereo" else "1.0"
    n = int(_numero(stream.get("channels")) or 0)
    return {1: "1.0", 2: "2.0", 3: "2.1", 4: "4.0", 5: "5.0", 6: "5.1", 7: "6.1", 8: "7.1"}.get(n) or (f"{n}ch" if n else None)


def _tracce_audio(streams):
    """Elenco delle tracce audio, es. ["ITA E-AC3 5.1", "ENG TrueHD Atmos 7.1"] (lingua, codec, canali)."""
    tracce = []
    for st in streams:
        if st.get("codec_type") != "audio":
            continue
        tag = {str(k).lower(): v for k, v in (st.get("tags") or {}).items()}
        lingua = str(tag.get("language") or "").upper()
        parti = [lingua] if lingua and lingua != "UND" else []
        parti.append(_codec_audio(st))
        canali = _canali_testo(st)
        if canali:
            parti.append(canali)
        tracce.append(" ".join(parti))
    if len(tracce) > 8:
        tracce = tracce[:8] + [f"+{len(tracce) - 8}"]
    return tracce or None


def _bit_video(video):
    """Bit per canale del video: dal campo bits_per_raw_sample, altrimenti dal formato dei pixel (pix_fmt)."""
    raw = _numero(video.get("bits_per_raw_sample"))
    if raw:
        return int(raw)
    pf = str(video.get("pix_fmt") or "")
    alto = re.search(r"(?:p0?|[a-z])(9|10|12|14|16)(?:le|be)$", pf)  # yuv420p10le, p010le, gbrp12le, gray10le (non nv12!)
    if alto:
        return int(alto.group(1))
    if re.search(r"(yuvj?4\d\dp|nv12|nv21|gray|gbrp|rgb24|bgr24|pal8|yuyv422|uyvy422|rgba?|bgra?|argb|abgr)$", pf):
        return 8
    return None


def _profilo(video):
    p = str(video.get("profile") or "").strip()
    return None if p.lower() in ("", "unknown") or p.startswith("-") else p


def _livello(video):
    """Livello del codec nella notazione abituale (es. 5.1). ffprobe lo dà come numero che dipende dal codec."""
    liv = _numero(video.get("level"))
    if liv is None or liv <= 0:
        return None
    liv, codec = int(liv), video.get("codec_name")
    if codec == "hevc":
        return f"{liv // 30}.{(liv % 30) // 3}"      # 153 -> 5.1
    if codec == "h264":
        return f"{liv // 10}.{liv % 10}"             # 41 -> 4.1
    if codec == "av1":
        return f"{2 + (liv >> 2)}.{liv & 3}"         # indice del livello -> 4.0, 5.1...
    return None


# codec audio senza perdita (lossless); il PCM (wav, aiff...) si riconosce dal prefisso "pcm"
_CODEC_LOSSLESS = {"flac", "alac", "ape", "wavpack", "tta", "wmalossless", "mlp", "truehd", "shorten", "tak"}


def _lossless(stream):
    """True se il codec audio non perde informazione (FLAC, ALAC, WAV...), False se è lossy (MP3, AAC, Opus...)."""
    nome = str(stream.get("codec_name") or "").lower()
    if nome.startswith("pcm") or nome in _CODEC_LOSSLESS:
        return True
    return nome == "dts" and "dts-hd ma" in str(stream.get("profile") or "").lower()


def _tag_minuscoli(*gruppi):
    """Unisce gruppi di tag con le chiavi in minuscolo (cambiano da formato a formato: TITLE, title, TIT2...);
    i primi gruppi hanno la precedenza."""
    unito = {}
    for gruppo in gruppi:
        if isinstance(gruppo, dict):
            for k, v in gruppo.items():
                unito.setdefault(str(k).lower(), v)
    return unito


def _primo_tag(tag, *nomi):
    """Il primo tag non vuoto tra `nomi` (testo ripulito e limitato a 200 caratteri), oppure None."""
    for nome in nomi:
        valore = str(tag.get(nome) or "").strip()
        if valore:
            return valore[:200]
    return None


def _tag_musicali(formato, stream_audio):
    """Artista, album, titolo, anno e numero di traccia dai tag del file. ffprobe li mette nel contenitore
    (mp3, flac, m4a) oppure nel flusso audio (ogg, opus): si guardano entrambi."""
    tag = _tag_minuscoli(formato.get("tags"), (stream_audio or {}).get("tags"))
    anno = re.match(r"\s*(\d{4})", _primo_tag(tag, "date", "year", "originaldate", "originalyear", "tdrc") or "")
    traccia = re.match(r"\s*(\d{1,4})", _primo_tag(tag, "track", "tracknumber") or "")  # "3" oppure "3/12"
    anno = int(anno.group(1)) if anno and 1000 <= int(anno.group(1)) <= 2999 else None
    traccia = int(traccia.group(1)) if traccia and int(traccia.group(1)) > 0 else None
    return {"ar": _primo_tag(tag, "artist", "album_artist", "albumartist"), "al": _primo_tag(tag, "album"),
            "ti": _primo_tag(tag, "title"), "an": anno, "tr": traccia}


def analizza(percorso, ffprobe, annulla, dimensione=None, cache=None, modifica=None):
    """Restituisce un dizionario con valori NUMERICI grezzi (la formattazione la fa il browser).
    I campi senza valore non vengono inclusi: nel report risultano 'null' e compaiono come '-'.
    Con `cache` (e la data di modifica del file) ffprobe parte solo se il file è nuovo o cambiato."""
    if annulla.is_set():
        return None
    if dimensione is None:
        try:
            dimensione = os.path.getsize(percorso)
        except OSError:
            dimensione = 0
    nome = os.path.basename(percorso)
    ext = os.path.splitext(nome)[1].lstrip(".")
    rec = {"p": nome, "t": "Generico", "e": ext.upper(), "d": dimensione}
    if modifica is not None:
        rec["m"] = modifica // 1_000_000_000  # data di modifica in secondi (dai nanosecondi dell'elenco file)
    if not ffprobe or ext.lower() not in ESTENSIONI_MEDIA:
        return rec
    usa_cache = cache is not None and modifica is not None
    chiave = os.path.normcase(percorso)
    if usa_cache:
        trovato = cache.cerca(chiave, dimensione, modifica)
        if trovato is not None:
            return trovato
    try:
        dati = esegui_ffprobe(ffprobe, percorso)
    except (OSError, subprocess.SubprocessError, ValueError):
        return rec  # errore momentaneo (es. timeout): non lo ricordiamo, al prossimo giro si riprova

    fmt = dati.get("format", {})
    _imposta(rec, du=_numero(fmt.get("duration")), bi=_numero(fmt.get("bit_rate")))
    streams = dati.get("streams", [])
    # attached_pic = copertina incorporata in un mp3/flac: non è un vero video
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video:
        rec["t"] = "Video"
        mx, mc, mf = _luminanza_hdr(video)
        _imposta(rec, vc=str(video.get("codec_name", "")).upper(),
                 w=video.get("width"), h=video.get("height"),
                 f=_fps(video.get("avg_frame_rate")) or _fps(video.get("r_frame_rate")),
                 hdr=_is_hdr(video),
                 cb=_bit_video(video), pr=_profilo(video), lv=_livello(video),
                 ht=_tipo_hdr(video), mx=mx, mc=mc, mf=mf, at=_tracce_audio(streams))
        # Dolby Vision: ffprobe espone profilo, compatibilità della base layer e presenza dell'enhancement layer
        dovi = next((sd for sd in video.get("side_data_list", []) if sd.get("dv_profile") is not None), None)
        if dovi:
            profilo = _numero(dovi.get("dv_profile"))
            compat = _numero(dovi.get("dv_bl_signal_compatibility_id"))
            _imposta(rec, dvp=int(profilo) if profilo is not None else None,
                     dvc=int(compat) if compat is not None else None,
                     dve=True if dovi.get("el_present_flag") else None)
    if audio:
        frequenza = _numero(audio.get("sample_rate"))                       # Hz
        profondita = _numero(audio.get("bits_per_raw_sample")) or _numero(audio.get("bits_per_sample"))
        _imposta(rec, ac=str(audio.get("codec_name", "")).upper(),
                 ch=audio.get("channels"), cl=audio.get("channel_layout"),
                 sr=int(frequenza) if frequenza else None,
                 bd=int(profondita) if profondita else None)                # assente nei formati lossy
        if not video:
            rec["t"] = "Audio"
            # i video veri sono già esclusi sopra: se resta un flusso video è la copertina incorporata
            copertina = any(s.get("codec_type") == "video" for s in streams)
            _imposta(rec, lo=_lossless(audio), cp=True if copertina else None, **_tag_musicali(fmt, audio))
    if usa_cache:
        cache.registra(chiave, dimensione, modifica, rec)
    return rec


# ---------------------------------------------------------------- impostazioni

def percorso_config():
    base = (os.environ.get("APPDATA") if IS_WIN else os.path.join(os.path.expanduser("~"), ".config")) \
        or os.path.expanduser("~")
    return os.path.join(base, "MediaDirLister", "config.json")


def carica_config():
    try:
        with open(percorso_config(), encoding="utf-8") as f:
            dati = json.load(f)
        return dati if isinstance(dati, dict) else {}
    except (OSError, ValueError):
        return {}


def salva_config(config):
    """Scrittura atomica: si scrive un file temporaneo e poi lo si sostituisce, così un blocco a metà
    non lascia un config.json troncato (e si perderebbero profili e colonne)."""
    percorso = percorso_config()
    temporaneo = percorso + ".tmp"
    try:
        os.makedirs(os.path.dirname(percorso), exist_ok=True)
        with open(temporaneo, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        os.replace(temporaneo, percorso)
    except (OSError, TypeError, ValueError):
        try:
            os.remove(temporaneo)
        except OSError:
            pass  # non è critico: al massimo la cartella non viene ricordata


# ---------------------------------------------------------------- profili (esclusioni + colonne)

COLONNE_TAG_MUSICA = ["artista", "album", "titolo", "anno", "traccia", "qualita", "copertina"]  # tag musicali (v3.9g)
# «Tipo» non c'è: in questi profili è uguale su ogni riga. Nel profilo Film non ci sono Codec audio e Canali audio:
# «Tracce audio» li contiene già (per tutte le tracce, con la lingua e il nome leggibile del codec)
COLONNE_MUSICA = ["nome", "artista", "album", "titolo", "anno", "traccia", "est", "dim", "durata", "ca",
                  "canali", "formato", "qualita", "copertina", "bitrate"]
COLONNE_FILM = ["nome", "est", "dim", "durata", "ris", "colore", "hdr", "dv", "fps", "cv", "tracce", "bitrate"]
TIPI_PROFILO = ("generale", "musica", "film")  # il tipo dice su quale modello di colonne si basa il profilo
TIPO_DA_NOME = {"Generale": "generale", "Musica": "musica", "Film": "film"}  # per i profili già esistenti con questi nomi
COLONNE_PER_TIPO = {"generale": COLONNE, "musica": COLONNE_MUSICA, "film": COLONNE_FILM}
MAX_NOME_PROFILO = 40


def profili_predefiniti():
    """I profili con cui si parte: ognuno ha le sue esclusioni e le sue colonne e si può modificare dalla finestra."""
    def profilo(colonne, tipo):  # liste nuove per ogni profilo: nessuna è condivisa con gli altri
        return {"estensioni_escluse": sorted(ESTENSIONI_ESCLUSE), "nomi_esclusi": sorted(NOMI_ESCLUSI),
                "colonne": list(colonne), "tipo": tipo, "sorgente": "", "mostra": "percorso", "dividi": False,
                "usa_cache": True}
    return {"Generale": profilo(COLONNE, "generale"), "Musica": profilo(COLONNE_MUSICA, "musica"),
            "Film": profilo(COLONNE_FILM, "film")}


def normalizza_estensioni(testo, scartate=None):
    """Estensioni da un testo libero (spazi, virgole, ; o a capo; il punto iniziale è facoltativo): minuscole, senza doppioni.
    Le voci non valide vengono aggiunte alla lista `scartate`, se data."""
    parti = re.split(r"[\s,;]+", testo) if isinstance(testo, str) else [str(x) for x in testo]
    risultato = []
    for voce in parti:
        voce = voce.strip()
        if not voce:
            continue
        pulita = voce.lower().lstrip("*").strip(".")
        if re.fullmatch(r"[a-z0-9_+-]{1,20}", pulita):
            if pulita not in risultato:
                risultato.append(pulita)
        elif scartate is not None:
            scartate.append(voce)
    return sorted(risultato)


def normalizza_nomi(testo, scartate=None):
    """Nomi completi di file da un testo (uno per riga, oppure separati da ; o virgole): minuscoli, senza doppioni."""
    parti = re.split(r"[\n;,]+", testo) if isinstance(testo, str) else [str(x) for x in testo]
    risultato = []
    for voce in parti:
        voce = voce.strip()
        if not voce:
            continue
        if "/" in voce or "\\" in voce or len(voce) > 255:    # un nome di file non contiene separatori di percorso
            if scartate is not None:
                scartate.append(voce)
            continue
        if voce.lower() not in risultato:
            risultato.append(voce.lower())
    return sorted(risultato)


def pulisci_profilo(dati):
    """Rende valido un profilo letto da config.json (il file può essere stato modificato a mano). None se non è un profilo."""
    if not isinstance(dati, dict):
        return None
    predefinito = profili_predefiniti()["Generale"]
    estensioni = normalizza_estensioni(dati["estensioni_escluse"]) if isinstance(dati.get("estensioni_escluse"), list) else predefinito["estensioni_escluse"]
    nomi = normalizza_nomi(dati["nomi_esclusi"]) if isinstance(dati.get("nomi_esclusi"), list) else predefinito["nomi_esclusi"]
    colonne = [c for c in COLONNE if isinstance(dati.get("colonne"), list) and c in dati["colonne"]] or list(COLONNE)
    # tipo, cartella sorgente e opzioni: None = mancante o non valido (lo completa carica_profili)
    return {"estensioni_escluse": estensioni, "nomi_esclusi": nomi, "colonne": colonne,
            "tipo": dati.get("tipo") if dati.get("tipo") in TIPI_PROFILO else None,
            "sorgente": dati["sorgente"].strip() if isinstance(dati.get("sorgente"), str) else "",
            "mostra": dati.get("mostra") if dati.get("mostra") in ("percorso", "nome") else None,
            "dividi": dati["dividi"] if isinstance(dati.get("dividi"), bool) else None,
            "usa_cache": dati["usa_cache"] if isinstance(dati.get("usa_cache"), bool) else None}


def carica_profili(config):
    """(profili, nome_del_profilo_attivo). Se non ci sono profili salvati si parte da quelli predefiniti, portando
    nel profilo «Generale» le colonne scelte nelle versioni precedenti; ne resta sempre almeno uno."""
    profili = {}
    grezzi = config.get("profili")
    if isinstance(grezzi, dict):
        for nome, dati in grezzi.items():
            nome = nome.strip() if isinstance(nome, str) else ""
            profilo = pulisci_profilo(dati)
            if nome and profilo is not None and nome not in profili:
                profili[nome] = profilo
    if profili and config.get("migrazione_3_9g") is not True and "Musica" in profili:
        nuove = set(COLONNE_TAG_MUSICA) | {"data"}  # una volta sola: poi le colonne si scelgono dalla finestra
        profili["Musica"]["colonne"] = [c for c in COLONNE if c in nuove or c in profili["Musica"]["colonne"]]
    if profili and config.get("migrazione_3_9t") is not True:
        # una volta sola, per i profili Film e Musica già salvati: si tolgono solo le colonne ridondanti (Tipo; nel Film
        # anche Codec audio e Canali audio, se c'è Tracce audio che li contiene). Il resto delle scelte non si tocca e dopo
        # le colonne si cambiano dalla finestra come sempre.
        for nome, togliere in (("Film", {"tipo", "ca", "canali"}), ("Musica", {"tipo"})):
            if nome in profili:
                colonne = profili[nome]["colonne"]
                if "tracce" not in colonne:
                    togliere = togliere & {"tipo"}  # senza Tracce audio, codec e canali sono l'unica informazione audio
                rimaste = [c for c in colonne if c not in togliere]
                if rimaste:
                    profili[nome]["colonne"] = rimaste
    if not profili:
        profili = profili_predefiniti()
        vecchie = config.get("colonne")
        if isinstance(vecchie, list):
            valide = [c for c in COLONNE if c in vecchie]
            if valide:
                profili["Generale"]["colonne"] = valide
    attivo = config.get("profilo_attivo")
    if attivo not in profili:
        attivo = "Generale" if "Generale" in profili else next(iter(profili))
    # profili salvati da versioni precedenti: il tipo si ricava dal nome, le opzioni ripartono da quelle che si usavano
    # (prima valevano per tutti), la cartella sorgente da quella usata per ultima, ma solo per il profilo attivo
    mostra = config.get("mostra_cartella") if config.get("mostra_cartella") in ("percorso", "nome") else "percorso"
    for nome, profilo in profili.items():
        profilo["tipo"] = profilo["tipo"] or TIPO_DA_NOME.get(nome, "generale")
        profilo["mostra"] = profilo["mostra"] or mostra
        if profilo["dividi"] is None:
            profilo["dividi"] = config.get("dividi_sottocartelle") is True
        if profilo["usa_cache"] is None:
            profilo["usa_cache"] = config.get("usa_cache", True) is not False
    if not any(profilo["sorgente"] for profilo in profili.values()):
        recenti = cartelle_recenti(config, controlla=False)
        if recenti:
            profili[attivo]["sorgente"] = recenti[0]
    return profili, attivo


def errore_nome_profilo(nome, esistenti, ignora=None):
    """Chiave di traduzione dell'errore se il nome non va bene (vuoto, troppo lungo, già usato), altrimenti None."""
    if not nome:
        return "nome_vuoto"
    if len(nome) > MAX_NOME_PROFILO:
        return "nome_lungo"
    if any(e.lower() == nome.lower() and e != ignora for e in esistenti):
        return "nome_esiste"
    return None


def cartelle_recenti(config, controlla=True):
    """Elenco delle cartelle scansionate, dalla più recente. Con controlla=True tiene solo quelle che esistono
    ancora; all'avvio si usa controlla=False perché isdir() su un disco di rete irraggiungibile può bloccarsi
    per decine di secondi, e la finestra non comparirebbe."""
    elenco = config.get("cartelle_recenti")
    if not isinstance(elenco, list):  # compatibilità con la versione precedente (una sola cartella)
        vecchia = config.get("cartella_scansione")
        elenco = [vecchia] if isinstance(vecchia, str) else []
    return [c for c in elenco if isinstance(c, str) and (not controlla or os.path.isdir(c))]


# ---------------------------------------------------------------- cache delle scansioni

FORMATO_CACHE = 1  # cambia solo se cambia la struttura dei record in cache, non i dati dei file (il passaggio a SQLite non la cambia)
GIORNI_CACHE = 180  # le voci che nessuna scansione completa ha riconfermato per tanti giorni si eliminano (cartelle o dischi non più usati)


def _rappresenta(valore):
    """Testo stabile tra un avvio e l'altro: gli insiemi (set) hanno un ordine casuale, quindi si ordinano."""
    if hasattr(valore, "co_code"):                       # oggetto codice: funzioni annidate e lambda
        return "<" + _impronta_codice(valore) + ">"
    if isinstance(valore, (tuple, list)):
        return "(" + ",".join(_rappresenta(v) for v in valore) + ")"
    if isinstance(valore, (set, frozenset)):
        return "{" + ",".join(sorted(_rappresenta(v) for v in valore)) + "}"
    return repr(valore)


def _impronta_codice(codice):
    """Impronta del codice compilato di una funzione (ignora commenti, spazi e numeri di riga)."""
    h = hashlib.sha1()
    h.update(codice.co_code)
    for parte in (codice.co_names, codice.co_varnames, codice.co_consts):
        h.update(_rappresenta(parte).encode("utf-8"))
    return h.hexdigest()[:12]


def _versione_cache():
    """La versione della cache si calcola dal codice che produce i dati dei file: se lo si modifica (nuove colonne,
    nuovi campi, nuove regole) cambia da sola e le voci vecchie vengono scartate, senza doverla aumentare a mano."""
    h = hashlib.sha1()
    for funzione in (esegui_ffprobe, _codec_audio, _canali_testo, _tracce_audio, _numero, _fps, _is_hdr, _tipo_hdr, _rapporto, _luminanza_hdr, _bit_video,
                     _profilo, _livello, _imposta, _lossless, _tag_minuscoli, _primo_tag, _tag_musicali, analizza):
        h.update(_impronta_codice(funzione.__code__).encode("ascii"))
        h.update(_rappresenta(funzione.__defaults__).encode("utf-8"))
    h.update(_rappresenta(sorted(ESTENSIONI_MEDIA)).encode("utf-8"))   # quali file passano da ffprobe
    h.update(_rappresenta(sorted(_NOMI_CODEC_AUDIO.items())).encode("utf-8"))   # tabelle usate dalle funzioni sopra
    h.update(_rappresenta(sorted(_CODEC_LOSSLESS)).encode("utf-8"))
    return f"{FORMATO_CACHE}-{h.hexdigest()[:10]}"


CACHE_VERSIONE = _versione_cache()


def percorso_cache():
    return os.path.join(os.path.dirname(percorso_config()), "cache_scansioni.db")


def percorso_cache_json():
    """Cache delle versioni fino alla 3.9g (un unico file JSON): si importa una volta sola e poi si elimina."""
    return os.path.join(os.path.dirname(percorso_config()), "cache_scansioni.json")


def svuota_cache_su_disco():
    """Elimina la cache (e l'eventuale vecchia cache JSON). True se c'era qualcosa da eliminare; OSError se non ci riesce."""
    trovata = False
    for percorso in (percorso_cache(), percorso_cache() + "-journal", percorso_cache_json()):
        try:
            os.remove(percorso)
            trovata = True
        except FileNotFoundError:
            pass
    return trovata


def _limite_superiore(prefisso):
    """Primo testo che viene dopo tutti quelli che iniziano con `prefisso`: serve a cercare una cartella intera
    con un intervallo (chiave >= prefisso AND chiave < limite), che usa l'indice invece di scorrere tutta la tabella."""
    return prefisso[:-1] + chr(ord(prefisso[-1]) + 1)


class CacheScansioni:
    """Ricorda l'esito di ffprobe per ogni file in un database SQLite: ffprobe viene rilanciato solo se il file è
    nuovo, se cambiano dimensione o data di modifica, oppure se cambia la versione di ffprobe (o del codice).

    All'apertura si leggono solo le voci della cartella da scansionare; al termine si scrivono solo le righe nuove
    o cambiate, in un'unica transazione (un blocco a metà non rovina la cache). Il database è usato solo dal
    thread di lavoro: i thread di analisi toccano soltanto i dizionari in memoria."""

    def __init__(self, versione_ff):
        self.versione_ff = versione_ff
        self._ff = versione_ff or ""
        self.vecchia = {}      # voci della cartella lette dal disco: {percorso: [dimensione, data_modifica_ns, record]}
        self.nuova = {}        # voci valide in questa scansione
        self.da_scrivere = {}  # tra queste, solo quelle nuove o cambiate (le uniche righe da scrivere)
        self.dalla_cache = 0
        self.analizzati = 0
        self._azzera = False   # il database è di un'altra versione (o è nuovo): al salvataggio si ricomincia da zero
        self._lock = threading.Lock()

    @staticmethod
    def _apri():
        """Apre (o crea) il database. Se il file è rovinato lo ricrea: la cache è solo un acceleratore.
        Restituisce None se non si riesce (disco pieno, file bloccato...): in quel caso si lavora senza cache."""
        for tentativo in (1, 2):
            try:
                os.makedirs(os.path.dirname(percorso_cache()), exist_ok=True)
                conn = sqlite3.connect(percorso_cache(), timeout=10)
                try:
                    conn.execute("CREATE TABLE IF NOT EXISTS meta (chiave TEXT PRIMARY KEY, valore TEXT)")
                    conn.execute("CREATE TABLE IF NOT EXISTS file (chiave TEXT PRIMARY KEY, dimensione INTEGER, "
                                 "modifica INTEGER, record TEXT NOT NULL, visto INTEGER NOT NULL) WITHOUT ROWID")
                    conn.commit()
                    return conn
                except sqlite3.Error:
                    conn.close()
                    raise
            except sqlite3.OperationalError:
                return None  # bloccato da un'altra istanza o disco non scrivibile: non è un file rovinato
            except sqlite3.DatabaseError:  # "file is not a database", "malformed": si elimina e si riprova
                try:
                    os.remove(percorso_cache())
                except OSError:
                    return None
            except (sqlite3.Error, OSError):
                return None
        return None

    def _importa_json(self, conn):
        """Primo avvio dopo l'aggiornamento: porta nel database la vecchia cache JSON (se è ancora valida),
        così non si rianalizzano tutti i file; poi la elimina."""
        vecchio = percorso_cache_json()
        if not os.path.exists(vecchio):
            return
        try:
            with open(vecchio, encoding="utf-8") as f:
                dati = json.load(f)
            if (dati.get("versione") == CACHE_VERSIONE and (dati.get("ffprobe") or "") == self._ff
                    and isinstance(dati.get("file"), dict)):
                adesso = int(time.time())
                righe = [(k, v[0], v[1], json.dumps(v[2], ensure_ascii=False, separators=(",", ":")), adesso)
                         for k, v in dati["file"].items()
                         if isinstance(v, list) and len(v) == 3 and isinstance(v[0], int)
                         and isinstance(v[1], int) and isinstance(v[2], dict)]
                with conn:
                    conn.executemany("INSERT OR REPLACE INTO file VALUES (?, ?, ?, ?, ?)", righe)
                    conn.executemany("INSERT OR REPLACE INTO meta VALUES (?, ?)",
                                     [("versione", CACHE_VERSIONE), ("ffprobe", self._ff)])
        except sqlite3.Error:
            return  # riproverà al prossimo avvio: il JSON resta dov'è
        except (OSError, ValueError, AttributeError, TypeError):
            pass  # JSON illeggibile o di un'altra versione: non serve più
        try:
            os.remove(vecchio)
        except OSError:
            pass

    def carica(self, cartella):
        """Legge dal database solo le voci della `cartella` che si sta per scansionare."""
        prefisso = os.path.normcase(cartella).rstrip(os.sep) + os.sep
        conn = self._apri()
        if conn is None:
            return
        try:
            meta = dict(conn.execute("SELECT chiave, valore FROM meta"))
            if not meta:
                self._importa_json(conn)
                meta = dict(conn.execute("SELECT chiave, valore FROM meta"))
            if meta.get("versione") != CACHE_VERSIONE or meta.get("ffprobe") != self._ff:
                self._azzera = True  # database nuovo oppure di un'altra versione di codice/ffprobe: voci non valide
                return
            for chiave, dimensione, modifica, record in conn.execute(
                    "SELECT chiave, dimensione, modifica, record FROM file WHERE chiave >= ? AND chiave < ?",
                    (prefisso, _limite_superiore(prefisso))):
                try:
                    self.vecchia[chiave] = [dimensione, modifica, json.loads(record)]
                except ValueError:
                    pass  # riga rovinata: quel file verrà rianalizzato
        except sqlite3.OperationalError:
            self.vecchia = {}
        except sqlite3.DatabaseError:  # file rovinato: lo si elimina, al salvataggio si ricrea
            self.vecchia, self._azzera = {}, True
            conn.close()
            try:
                os.remove(percorso_cache())
            except OSError:
                pass
        finally:
            conn.close()

    def cerca(self, chiave, dimensione, modifica):
        voce = self.vecchia.get(chiave)
        if not (isinstance(voce, list) and len(voce) == 3 and voce[0] == dimensione
                and voce[1] == modifica and isinstance(voce[2], dict)):
            return None
        with self._lock:
            self.dalla_cache += 1
        self.nuova[chiave] = voce
        return voce[2]

    def registra(self, chiave, dimensione, modifica, rec):
        voce = [dimensione, modifica, rec]
        with self._lock:
            self.analizzati += 1
        self.nuova[chiave] = voce
        self.da_scrivere[chiave] = voce

    def salva(self, cartella, pota=True):
        """Scrive su disco solo ciò che è cambiato. pota=True: elimina i file di `cartella` che non esistono più
        e conferma tutti gli altri (data dell'ultimo controllo). pota=False (scansione annullata): conserva anche
        le voci vecchie non ancora riesaminate. In ogni caso elimina le voci non confermate da più di GIORNI_CACHE giorni."""
        prefisso = os.path.normcase(cartella).rstrip(os.sep) + os.sep
        adesso = int(time.time())
        conn = self._apri()
        if conn is None:
            return  # la cache è solo un acceleratore: se non si salva, nessun danno
        try:
            with conn:  # un'unica transazione: o si scrive tutto o niente
                if self._azzera:
                    conn.execute("DELETE FROM file")
                    conn.executemany("INSERT OR REPLACE INTO meta VALUES (?, ?)",
                                     [("versione", CACHE_VERSIONE), ("ffprobe", self._ff)])
                if pota:
                    conn.executemany("DELETE FROM file WHERE chiave = ?",
                                     [(k,) for k in self.vecchia if k not in self.nuova])
                    conn.execute("UPDATE file SET visto = ? WHERE chiave >= ? AND chiave < ?",
                                 (adesso, prefisso, _limite_superiore(prefisso)))
                conn.executemany(
                    "INSERT OR REPLACE INTO file VALUES (?, ?, ?, ?, ?)",
                    [(k, v[0], v[1], json.dumps(v[2], ensure_ascii=False, separators=(",", ":")), adesso)
                     for k, v in self.da_scrivere.items()])
                conn.execute("DELETE FROM file WHERE visto < ?", (adesso - GIORNI_CACHE * 86400,))
            self._azzera = False
        except (sqlite3.Error, OSError, ValueError, TypeError):
            pass
        finally:
            conn.close()


# ---------------------------------------------------------------- report HTML

CSS = """
/* temi: scuro (predefinito) e chiaro; la scelta si cambia con il pulsante e si ricorda nel browser */
:root{color-scheme:dark;--sfondo:#2b2b2b;--pannello:#1e1e1e;--testo:#e0e0e0;--titolo:#0d6efd;--campo:#333;--campo-testo:#fff;--bordo:#555;--bordo-tab:#444;--testata:#212529;--testata-testo:#fff;--riga-pari:#2a2a2a;--btn-hover:#3d3d3d;--accento:#0d6efd;--disabilitato:#555;--gruppo:#1f3b63;--gruppo-testo:#fff}
:root[data-tema="chiaro"]{color-scheme:light;--sfondo:#eef1f5;--pannello:#fff;--testo:#1f2937;--titolo:#0b5ed7;--campo:#fff;--campo-testo:#111827;--bordo:#bcc5d1;--bordo-tab:#d5dbe3;--testata:#e6ebf2;--testata-testo:#1f2937;--riga-pari:#f4f6f9;--btn-hover:#eef2f7;--accento:#0b5ed7;--disabilitato:#a8b2c0;--gruppo:#dbe7f7;--gruppo-testo:#12305b}
body{font-family:sans-serif;padding:20px;background:var(--sfondo);color:var(--testo)}
.container{background:var(--pannello);padding:20px;border-radius:8px}
h2{color:var(--titolo)}
.percorso{font-size:22px;word-break:break-all}
input,select{padding:8px;background:var(--campo);color:var(--campo-testo);border:1px solid var(--bordo);border-radius:4px;font-size:14px}
input{width:100%;max-width:260px}
.filtri{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:15px}
.gruppo{display:flex;gap:6px}
.fbtn{padding:8px 14px;background:var(--campo);color:var(--testo);border:1px solid var(--bordo);border-radius:4px;cursor:pointer;font-size:14px}
.fbtn:hover{background:var(--btn-hover)}
.fbtn.attivo{background:var(--accento);border-color:var(--accento);color:#fff}
#fStampa{background:#c74e00;border-color:#c74e00;color:#fff;font-weight:bold}
#fStampa:hover{background:#a84300;border-color:#a84300}
tr.grp td{background:var(--gruppo);color:var(--gruppo-testo);font-weight:bold;font-size:15px}
.tabella{overflow-x:auto}
table{width:100%;border-collapse:collapse;margin-top:10px;font-size:14px}
th,td{padding:10px;border:1px solid var(--bordo-tab);text-align:left}
th{background:var(--testata);color:var(--testata-testo);cursor:pointer;white-space:nowrap;user-select:none}
tr:nth-child(even){background:var(--riga-pari)}
.badge{padding:4px 8px;border-radius:4px;font-size:12px;font-weight:bold;color:#fff;display:inline-block}
.bg-danger{background:#dc3545}.bg-primary{background:#0d6efd}.bg-secondary{background:#6c757d}
.paginazione{margin:15px 0;display:flex;gap:8px;align-items:center}
.pag-btn{padding:5px 10px;background:var(--accento);color:#fff;border:none;border-radius:4px;cursor:pointer}
.pag-btn:disabled{background:var(--disabilitato);cursor:not-allowed}
.pannello-col{display:flex;flex-wrap:wrap;gap:10px 32px;align-items:flex-start;border:1px solid var(--bordo);border-radius:6px;padding:12px 16px;margin-bottom:15px}
.pannello-col[hidden]{display:none}
.pc-gruppo{display:flex;flex-direction:column;gap:5px;min-width:150px}
.pc-gruppo b{font-size:13px;color:var(--titolo)}
.pc-gruppo label{display:flex;gap:7px;align-items:center;cursor:pointer;font-size:14px;white-space:nowrap}
.pannello-col input{width:auto;max-width:none;padding:0;margin:0}
.pc-azioni{display:flex;flex-direction:column;gap:6px;margin-left:auto}
.riepilogo{border:1px solid var(--bordo);border-radius:6px;padding:12px 16px;margin-bottom:15px}
.riep-testa{display:flex;align-items:center;gap:8px;width:100%;background:none;border:0;padding:0;color:var(--titolo);font-size:15px;font-weight:600;cursor:pointer;text-align:left}
.riep-tot{margin:6px 0 0;font-size:14px}
.riep-gruppi{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px 26px;margin-top:12px}
.riep-gruppi[hidden]{display:none}
.riep-gruppi h3{margin:0 0 6px;font-size:13px;color:var(--titolo)}
.riep-riga{display:grid;grid-template-columns:minmax(70px,max-content) 1fr 46px;gap:8px;align-items:center;width:100%;background:none;border:0;border-radius:4px;padding:3px 4px;color:var(--testo);font-size:13px;text-align:left;box-sizing:border-box}
button.riep-riga{cursor:pointer}
button.riep-riga:hover{background:var(--btn-hover)}
.riep-riga.attivo{background:var(--gruppo);color:var(--gruppo-testo)}
.riep-barra{height:8px;background:var(--bordo-tab);border-radius:4px;overflow:hidden}
.riep-barra i{display:block;height:100%;background:var(--accento);border-radius:4px;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.riep-n{text-align:right}
.riep-altri{opacity:.75}
.solo-stampa{display:none}
@page{size:A4 landscape;margin:10mm}
@media print{
*{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{background:#fff;color:#000;padding:0;font-size:10pt}
.container{background:#fff;padding:0;border-radius:0}
h2{color:#000;font-size:16pt;margin:0 0 6px}
p{margin:2px 0;color:#000}
.percorso{font-size:11pt;word-break:break-all}
.filtri,.paginazione,.ord,.pannello-col,.riep-freccia{display:none}
.solo-stampa{display:block}
.tabella{overflow:visible}
table{font-size:8.5pt;margin-top:8px}
th,td{padding:3px 5px;border:1px solid #888;color:#000;overflow-wrap:break-word}
th{background:#e5e5e5;cursor:default;white-space:normal}
thead{display:table-header-group}
tr{break-inside:avoid}
tr:nth-child(even){background:#f2f2f2}
.badge{background:none !important;color:#000;border:1px solid #000;padding:0 4px;font-size:8pt}
tr.grp{break-after:avoid}
tr.grp td{background:#d9d9d9;color:#000;font-size:10pt;border-top:2px solid #000}
}
"""

JS = r"""
let perPagina = 50;   // risultati per pagina (scelti dal menu)
const SOGLIA_UNICA = 5000;   // oltre questi file la pagina unica rallenta il browser: si chiede conferma
const BADGE = {Video: 'danger', Audio: 'primary'};
const p2 = n => String(n).padStart(2, '0');
const fmtDim = b => b >= 1073741824 ? (b / 1073741824).toFixed(2) + ' GB' : (b / 1048576).toFixed(2) + ' MB';
const fmtDur = s => {
  if (s == null) return '-';
  s = Math.floor(s);
  const o = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), c = s % 60;
  return o ? `${o}:${p2(m)}:${p2(c)}` : `${p2(m)}:${p2(c)}`;
};
const dash = v => (v == null || v === '') ? '-' : String(v);
// data di modifica (secondi) nel formato della lingua del report: 17/10/2026 oppure 2026-10-17
const fmtData = s => {
  const d = new Date(s * 1000), a = d.getFullYear(), me = p2(d.getMonth() + 1), g = p2(d.getDate());
  return L.fmt_data === 'ymd' ? `${a}-${me}-${g}` : `${g}/${me}/${a}`;
};

// HDR: "HDR10", "HLG", "HDR10 + DV", "Dolby Vision", con il picco di luminanza del master se noto
const fmtHdr = m => {
  if (m.hdr == null) return '-';
  if (!m.hdr) return L.no;
  const tipi = [];
  if (m.ht) tipi.push(m.ht);
  if (m.dvp != null) tipi.push(m.ht ? 'DV' : 'Dolby Vision');
  let s = tipi.length ? tipi.join(' + ') : L.si;   // HDR di tipo non riconosciuto
  if (m.mx) s += ' · ' + m.mx + ' nit';
  return s;
};
const tipHdr = m => {   // dettagli nel suggerimento che compare passando il mouse
  const p = [];
  if (m.mx) p.push('Mastering: ' + m.mx + ' nit');
  if (m.mc) p.push('MaxCLL: ' + m.mc);
  if (m.mf) p.push('MaxFALL: ' + m.mf);
  return p.join(' · ');
};
// ordine: senza HDR, HLG, HDR10, Dolby Vision senza base, HDR10/HLG + Dolby Vision
const rangoHdr = m => m.hdr == null ? null : (m.ht === 'HLG' ? 1 : m.ht === 'HDR10' ? 2 : 0) + (m.dvp != null ? 2 : 0) + (m.hdr && !m.ht && m.dvp == null ? 1 : 0);

// Profondità di colore: "10 bit · Main 10 @ L5.1"
const fmtColore = m => {
  if (m.t !== 'Video') return '-';
  const parti = [];
  if (m.cb) parti.push(m.cb + ' bit');
  if (m.pr) parti.push(m.pr + (m.lv ? ' @ L' + m.lv : ''));
  else if (m.lv) parti.push('L' + m.lv);
  return parti.length ? parti.join(' · ') : '-';
};

// Dolby Vision: "Profilo 8.1 (HDR10)", "Profilo 5", "Profilo 7 (con EL)"...
const BASE_DV = {1: 'HDR10', 2: 'SDR', 4: 'HLG'};
const fmtDV = m => {
  if (m.t !== 'Video') return '-';
  if (m.dvp == null) return L.no;
  let s = L.profilo + ' ' + m.dvp;
  if ((m.dvp === 8 || m.dvp === 10) && m.dvc != null) {
    s += '.' + m.dvc + (BASE_DV[m.dvc] ? ' (' + BASE_DV[m.dvc] + ')' : '');
  } else if (m.dvp === 7 && m.dve) {
    s += ' ' + L.con_el;                  // doppio layer: FEL o MEL (ffprobe non distingue i due casi)
  }
  return s;
};

// show = testo mostrato, key = valore usato per ordinare (numerico dove serve)
const TUTTE = [
  {id: 'nome', t: L.th.nome,   show: m => m.p,                          key: m => m.p.toLowerCase()},
  {id: 'artista', t: L.th.artista, show: m => dash(m.ar),                key: m => m.ar ? m.ar.toLowerCase() : null},
  {id: 'album',   t: L.th.album,   show: m => dash(m.al),                key: m => m.al ? m.al.toLowerCase() : null},
  {id: 'titolo',  t: L.th.titolo,  show: m => dash(m.ti),                key: m => m.ti ? m.ti.toLowerCase() : null},
  {id: 'anno',    t: L.th.anno,    show: m => dash(m.an),                key: m => m.an},
  {id: 'traccia', t: L.th.traccia, show: m => dash(m.tr),                key: m => m.tr},
  {id: 'tipo', t: L.th.tipo,        show: m => L.tipi[m.t] || m.t,                          key: m => m.t},
  {id: 'est', t: L.th.est,        show: m => m.e,                          key: m => m.e},
  {id: 'dim', t: L.th.dim,  show: m => fmtDim(m.d),                  key: m => m.d},
  {id: 'data', t: L.th.data,  show: m => m.m == null ? '-' : fmtData(m.m),   key: m => m.m},
  {id: 'durata', t: L.th.durata,      show: m => fmtDur(m.du),                 key: m => m.du},
  {id: 'ris', t: L.th.ris, show: m => m.w ? m.w + 'x' + m.h : '-',  key: m => m.w ? m.w * m.h : null},
  {id: 'colore',  t: L.th.colore,  show: fmtColore, key: m => m.t !== 'Video' || !m.cb ? null : m.cb},
  {id: 'hdr',     t: L.th.hdr,         show: fmtHdr, tip: tipHdr, key: rangoHdr},
  {id: 'dv',      t: L.th.dv, show: fmtDV, key: m => m.t !== 'Video' ? null : (m.dvp == null ? 0 : m.dvp * 10 + (m.dvc || 0))},
  {id: 'fps', t: L.th.fps,         show: m => dash(m.f),                    key: m => m.f},
  {id: 'cv', t: L.th.cv,     show: m => dash(m.vc),                   key: m => m.vc || null},
  {id: 'ca', t: L.th.ca,     show: m => dash(m.ac),                   key: m => m.ac || null},
  {id: 'canali',  t: L.th.canali, show: m => m.ch == null ? '-' : (m.cl ? m.cl + ' (' + m.ch + ')' : m.ch + ' ch'), key: m => m.ch},
  {id: 'formato', t: L.th.formato, show: m => m.sr == null ? '-' : parseFloat((m.sr / 1000).toFixed(3)) + ' kHz' + (m.bd ? ' · ' + m.bd + ' bit' : ''), key: m => m.sr == null ? null : m.sr * 100 + (m.bd || 0)},
  {id: 'qualita', t: L.th.qualita, show: m => m.lo == null ? '-' : (m.lo ? 'Lossless' : 'Lossy'), key: m => m.lo == null ? null : (m.lo ? 1 : 0)},
  {id: 'copertina', t: L.th.copertina, show: m => m.t !== 'Audio' ? '-' : (m.cp ? L.si : L.no), key: m => m.t !== 'Audio' ? null : (m.cp ? 1 : 0)},
  {id: 'tracce',  t: L.th.tracce,   show: m => m.t === 'Video' && m.at ? m.at.join(' · ') : '-',
   key: m => m.t === 'Video' && m.at ? m.at.length : null},
  {id: 'bitrate', t: L.th.bitrate,     show: m => m.bi == null ? '-' : Math.round(m.bi / 1000) + ' kbps', key: m => m.bi},
];
// colonne mostrate: all'apertura quelle scelte nella finestra del programma; dal pulsante "Colonne" si cambiano
// al volo (i dati di tutte le colonne sono comunque nel report)
const attive = new Set(VISIBILI);
let COLS = TUTTE.filter(c => attive.has(c.id));

let filtrati = [...DATI], vista = filtrati, pagina = 1, colOrd = -1, asc = true, unica = false, inStampa = false;
// raggruppamento per sottocartella: attivo se il report è stato generato con i dati delle cartelle
let raggruppa = CARTELLE.length > 0, statGruppi = new Map();
// testo di ricerca in minuscolo, calcolato una volta; '\n' impedisce match a cavallo di due campi
DATI.forEach(m => m._h = (m.p + '\n' + m.e + '\n' + (L.tipi[m.t] || m.t) + '\n' + (m.ar || '') + '\n' + (m.al || '') + '\n' + (m.ti || '')).toLowerCase());
const tbody = document.querySelector('#mTable tbody');
const info = document.getElementById('infoPagina');
const prec = document.getElementById('btnPrec');
const succ = document.getElementById('btnSucc');

const thead = document.querySelector('#mTable thead');
function costruisciIntestazione() {
  const riga = document.createElement('tr');
  COLS.forEach((c, i) => {
    const th = document.createElement('th');
    th.textContent = c.t;
    const freccia = document.createElement('span');   // la freccia dell'ordinamento non si stampa
    freccia.className = 'ord';
    freccia.textContent = ' ↕';
    th.appendChild(freccia);
    th.onclick = () => ordina(i);
    riga.appendChild(th);
  });
  thead.replaceChildren(riga);
}
costruisciIntestazione();

function intestazioneGruppo(k) {
  const g = statGruppi.get(k) || {n: 0, d: 0};
  const riga = document.createElement('tr');
  riga.className = 'grp';
  const td = document.createElement('td');
  td.colSpan = COLS.length;
  td.textContent = '📁 ' + (CARTELLE[k] || L.radice) + '  —  ' + g.n + ' ' + L.file + '  ·  ' + fmtDim(g.d);
  riga.appendChild(td);
  return riga;
}

function render() {
  const tutte = unica || inStampa;                  // in stampa escono tutti i risultati, non solo la pagina corrente
  const tot = tutte ? 1 : Math.max(1, Math.ceil(filtrati.length / perPagina));
  pagina = Math.min(pagina, tot);
  tbody.replaceChildren();
  const frag = document.createDocumentFragment();   // un solo inserimento nella pagina: molto più veloce
  const visibili = tutte ? vista : vista.slice((pagina - 1) * perPagina, pagina * perPagina);
  visibili.forEach((m, i, pag) => {
    // intestazione della sottocartella: a ogni cambio di gruppo e all'inizio di ogni pagina
    if (raggruppa && (i === 0 || pag[i - 1].k !== m.k)) frag.appendChild(intestazioneGruppo(m.k));
    const riga = document.createElement('tr');
    COLS.forEach(c => {
      const td = document.createElement('td');
      if (c.id === 'tipo') {
        const sp = document.createElement('span');
        sp.className = 'badge bg-' + (BADGE[m.t] || 'secondary');
        sp.textContent = L.tipi[m.t] || m.t;
        td.appendChild(sp);
      } else {
        td.textContent = c.show(m);   // textContent: i nomi dei file non vengono mai interpretati come HTML
        const sugg = c.tip && c.tip(m);
        if (sugg) td.title = sugg;
      }
      riga.appendChild(td);
    });
    frag.appendChild(riga);
  });
  tbody.appendChild(frag);
  const conteggio = `${L.mostrati}: ${filtrati.length}` + (filtrati.length !== DATI.length ? ` ${L.su} ${DATI.length}` : '');
  info.textContent = tutte ? `${L.pagina_unica} (${conteggio})` : `${L.pagina} ${pagina} ${L.di} ${tot} (${conteggio})`;
  prec.disabled = pagina <= 1;
  succ.disabled = pagina >= tot;
  selPP.disabled = unica;               // in pagina unica il numero per pagina non serve
}

function ordinaLista() {
  if (colOrd >= 0) ordinaPerColonna();
  // con il raggruppamento i file restano insieme per cartella (l'ordinamento è stabile: dentro ogni
  // gruppo vale l'ordine scelto)
  vista = raggruppa ? filtrati.slice().sort((a, b) => a.k - b.k) : filtrati;
}

function ordinaPerColonna() {
  const key = COLS[colOrd].key, dir = asc ? 1 : -1;
  // la chiave di ogni riga si calcola una volta sola, non a ogni confronto
  const righe = filtrati.map(m => [key(m), m]);
  righe.sort((a, b) => {
    const x = a[0], y = b[0];
    if (x == null && y == null) return 0;
    if (x == null) return 1;           // i valori mancanti vanno sempre in fondo
    if (y == null) return -1;
    return (x > y ? 1 : x < y ? -1 : 0) * dir;
  });
  filtrati = righe.map(r => r[1]);
}

function ordina(i) {
  if (colOrd === i) asc = !asc; else { colOrd = i; asc = true; }
  ordinaLista();
  pagina = 1;
  render();
}

// --- filtri: ricerca testuale, tipo, HDR e risoluzione si combinano tra loro
const filtro = {q: '', tipo: 'Tutti', hdr: false, res: null, giorni: null, riep: null};   // riep = riga del riepilogo scelta con un clic

// conRiep = false: tutti i filtri tranne quello scelto dal riepilogo (serve a mostrare, nel gruppo scelto, anche le alternative)
function passaFiltri(m, limite, conRiep) {
  return (filtro.tipo === 'Tutti' || m.t === filtro.tipo) &&
    (!filtro.hdr || m.hdr === true) &&
    // "sotto X" = sia larghezza sia altezza inferiori (così un film 1920x800 non è "sotto 1080p")
    (!filtro.res || (m.w != null && m.h != null && m.w < filtro.res[0] && m.h < filtro.res[1])) &&
    (!filtro.giorni || (m.m != null && m.m >= limite)) &&
    (!filtro.q || m._h.includes(filtro.q)) &&
    (!conRiep || !filtro.riep || valoreRiep(filtro.riep.gruppo, m) === filtro.riep.valore);
}

function applicaFiltri() {
  const limite = filtro.giorni ? Date.now() / 1000 - filtro.giorni * 86400 : 0;   // "ultimi N giorni" rispetto a ora
  filtrati = DATI.filter(m => passaFiltri(m, limite, true));
  // pagina unica: se i filtri allargano molto l'elenco, si chiede di nuovo conferma (altrimenti si torna alle pagine)
  if (unica && filtrati.length > SOGLIA_UNICA && !chiediUnica(filtrati.length)) {
    unica = false;
    bUnica.classList.remove('attivo');
  }
  statGruppi = new Map();              // quanti file e quanto spazio per ogni cartella (dopo i filtri)
  if (CARTELLE.length) for (const m of filtrati) {
    let g = statGruppi.get(m.k);
    if (!g) statGruppi.set(m.k, g = {n: 0, d: 0});
    g.n++; g.d += m.d;
  }
  aggiornaRiepilogo(limite);
  ordinaLista();                       // mantiene l'ordinamento scelto
  pagina = 1;
  render();
}

// --- riepilogo in testa al report: totali e ripartizioni dei file filtrati. Un clic su una riga filtra la tabella;
// nel gruppo scelto restano visibili anche le altre voci, così si può passare da una all'altra (come nei filtri di un negozio online)
const lingua = document.documentElement.lang || 'it';
const num = (n, dec) => n.toLocaleString(lingua, {maximumFractionDigits: dec || 0});
const fmtGrande = b => b >= 1099511627776 ? num(b / 1099511627776, 2) + ' TB' : b >= 1073741824 ? num(b / 1073741824, 2) + ' GB' : num(b / 1048576, 1) + ' MB';
const fmtOre = sec => (sec >= 36000 ? num(Math.round(sec / 3600)) : num(sec / 3600, 1)) + ' ' + L.riep_ore;
// risoluzione per larghezza (così 1920x800 è 1080p); i formati più quadrati (4:3, 1440x1080) si ricondurono al 16:9 dall'altezza
const classeRis = (w, h) => {
  const ef = h && w / h < 1.7 ? h * 16 / 9 : w;
  return ef >= 3200 ? '4K' : ef >= 2300 ? '1440p' : ef >= 1700 ? '1080p' : ef >= 1150 ? '720p' : L.riep_altro;
};
const etichettaHdr = m => {
  if (m.hdr == null) return null;
  if (!m.hdr) return L.riep_sdr;
  const t = [];
  if (m.ht) t.push(m.ht);
  if (m.dvp != null) t.push(m.ht ? 'DV' : 'Dolby Vision');
  return t.length ? t.join(' + ') : L.riep_hdr_altro;
};
// per = tipo di file a cui il gruppo si applica; val(m) = la voce in cui cade il file (null = non conta); fisso = ordine fisso
const GRUPPI_RIEP = [
  {id: 'ris', per: 'Video', fisso: ['4K', '1440p', '1080p', '720p'], val: m => m.w && m.h ? classeRis(m.w, m.h) : null},
  {id: 'hdr', per: 'Video', val: etichettaHdr},
  {id: 'cv', per: 'Video', val: m => m.vc || null},
  {id: 'ca', per: 'Video', val: m => m.ac || null},
  {id: 'caA', col: 'ca', per: 'Audio', val: m => m.ac || null},
  {id: 'formato', per: 'Audio', val: m => m.sr == null ? null : parseFloat((m.sr / 1000).toFixed(3)) + ' kHz' + (m.bd ? ' \u00b7 ' + m.bd + ' bit' : '')},
  {id: 'qualita', per: 'Audio', val: m => m.lo == null ? null : (m.lo ? 'Lossless' : 'Lossy')},
];
const valoreRiep = (g, m) => m.t === g.per ? g.val(m) : null;
const titoloGruppo = g => L.nomi_col[g.col || g.id] +
  ((g.id === 'ca' || g.id === 'caA') && haVideo && haAudio ? ' (' + (g.per === 'Video' ? L.riep_video : L.riep_brani) + ')' : '');
const MAX_RIGHE = 6;   // oltre, le voci meno frequenti si raccolgono in "Altri"

function impostaRiep(g, valore) {   // lo stesso clic due volte toglie il filtro
  const r = filtro.riep;
  filtro.riep = r && r.gruppo === g && r.valore === valore ? null : {gruppo: g, valore};
  applicaFiltri();
}

function rigaRiep(etichetta, n, max, attivo, g, valore) {
  const el = document.createElement(g ? 'button' : 'div');
  el.className = 'riep-riga' + (attivo ? ' attivo' : '') + (g ? '' : ' riep-altri');
  if (g) { el.type = 'button'; el.setAttribute('aria-pressed', String(attivo)); el.onclick = () => impostaRiep(g, valore); }
  const l = document.createElement('span'); l.textContent = etichetta;
  const barra = document.createElement('span'); barra.className = 'riep-barra';
  const i = document.createElement('i'); i.style.width = (max ? Math.max(n ? 2 : 0, n / max * 100) : 0) + '%'; barra.appendChild(i);
  const c = document.createElement('span'); c.className = 'riep-n'; c.textContent = num(n);
  el.append(l, barra, c);
  return el;
}

function aggiornaRiepilogo(limite) {
  let spazio = 0, durata = 0;
  const artisti = new Set(), album = new Set();
  for (const m of filtrati) {
    spazio += m.d || 0; durata += m.du || 0;
    if (m.t === 'Audio') { if (m.ar) artisti.add(m.ar); if (m.al) album.add((m.ar || '') + '\n' + m.al); }
  }
  document.getElementById('riepTot').textContent = [
    num(filtrati.length) + ' ' + L.file, fmtGrande(spazio), durata ? fmtOre(durata) : '',
    artisti.size ? num(artisti.size) + ' ' + L.riep_artisti : '', album.size ? num(album.size) + ' ' + L.riep_album : ''
  ].filter(Boolean).join(' \u00b7 ');
  const base = filtro.riep ? DATI.filter(m => passaFiltri(m, limite, false)) : filtrati;   // senza il filtro del riepilogo
  const corpo = document.getElementById('riepCorpo');
  corpo.replaceChildren();
  for (const g of GRUPPI_RIEP) {
    if (!(g.per === 'Video' ? haVideo : haAudio)) continue;
    const attivo = filtro.riep && filtro.riep.gruppo === g ? filtro.riep.valore : null;
    const conta = new Map();
    for (const m of (attivo !== null ? base : filtrati)) {
      const v = valoreRiep(g, m);
      if (v !== null) conta.set(v, (conta.get(v) || 0) + 1);
    }
    if (attivo !== null && !conta.has(attivo)) conta.set(attivo, 0);   // la voce scelta resta sempre visibile (per poterla togliere)
    if (!conta.size) continue;
    let voci = [...conta.entries()];
    if (g.fisso) {
      const pos = v => g.fisso.indexOf(v) < 0 ? 99 : g.fisso.indexOf(v);
      voci.sort((a, b) => pos(a[0]) - pos(b[0]));
    } else voci.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    let altri = 0;
    if (voci.length > MAX_RIGHE) {
      const tieni = voci.slice(0, MAX_RIGHE - 1);
      const scelta = voci.find(v => v[0] === attivo);
      if (scelta && !tieni.includes(scelta)) tieni[MAX_RIGHE - 2] = scelta;   // la voce scelta resta sempre visibile
      altri = voci.filter(v => !tieni.includes(v)).reduce((t, v) => t + v[1], 0);
      voci = tieni;
    }
    const max = Math.max(altri, ...voci.map(v => v[1]));
    const box = document.createElement('div');
    const h = document.createElement('h3'); h.textContent = titoloGruppo(g); box.appendChild(h);
    voci.forEach(([v, n]) => box.appendChild(rigaRiep(v, n, max, v === attivo, g, v)));
    if (altri) box.appendChild(rigaRiep(L.riep_altri, altri, max, false, null, null));
    corpo.appendChild(box);
  }
}

// apri/chiudi: chiuso resta la riga dei totali; la scelta si ricorda per questo report
const bRiep = document.getElementById('riepTesta');
const corpoRiep = document.getElementById('riepCorpo');
const mostraRiep = (aperto, salva) => {
  corpoRiep.hidden = !aperto;
  bRiep.setAttribute('aria-expanded', String(aperto));
  document.getElementById('riepFreccia').textContent = aperto ? '\u25be' : '\u25b8';
  if (salva) { try { localStorage.setItem('mdl-riep-' + ID_REPORT, aperto ? '1' : '0'); } catch (e) {} }
};
bRiep.onclick = () => mostraRiep(corpoRiep.hidden, true);
let riepAperto = true;
try { riepAperto = localStorage.getItem('mdl-riep-' + ID_REPORT) !== '0'; } catch (e) {}
mostraRiep(riepAperto, false);

// --- filtri sensati per il contenuto: un report di sola musica non offre Video, HDR e risoluzione; uno di soli
// film non offre i tag musicali. Conta ciò che c'è nel report, non il nome del profilo.
const haVideo = DATI.some(m => m.t === 'Video');
const haAudio = DATI.some(m => m.t === 'Audio');
if (!(haVideo && haAudio)) document.getElementById('gTipo').style.display = 'none';   // con un solo tipo, Tutti/Video/Audio non filtrerebbero nulla
if (!haVideo) {
  document.getElementById('fHdr').style.display = 'none';
  document.getElementById('fRes').style.display = 'none';
}
const bottoniTipo = document.querySelectorAll('#gTipo .fbtn');
bottoniTipo.forEach(b => b.onclick = () => {
  filtro.tipo = b.dataset.tipo;
  bottoniTipo.forEach(x => x.classList.toggle('attivo', x === b));
  applicaFiltri();
});
const bHdr = document.getElementById('fHdr');
bHdr.onclick = () => { filtro.hdr = !filtro.hdr; bHdr.classList.toggle('attivo', filtro.hdr); applicaFiltri(); };
const selRes = document.getElementById('fRes');
selRes.onchange = () => { filtro.res = selRes.value ? selRes.value.split(',').map(Number) : null; applicaFiltri(); };
const selData = document.getElementById('fData');
selData.onchange = () => { filtro.giorni = selData.value ? Number(selData.value) : null; applicaFiltri(); };
const inputCerca = document.getElementById('cercaInput');
let timer;
inputCerca.addEventListener('input', () => {
  clearTimeout(timer);
  timer = setTimeout(() => { filtro.q = inputCerca.value.toLowerCase(); applicaFiltri(); }, 200);
});
document.getElementById('fReset').onclick = () => {
  filtro.q = ''; filtro.tipo = 'Tutti'; filtro.hdr = false; filtro.res = null; filtro.giorni = null; filtro.riep = null;
  inputCerca.value = ''; selRes.value = ''; selData.value = '';
  bHdr.classList.remove('attivo');
  bottoniTipo.forEach(x => x.classList.toggle('attivo', x.dataset.tipo === 'Tutti'));
  applicaFiltri();
};
prec.onclick = () => { if (pagina > 1) { pagina--; render(); } };
succ.onclick = () => { pagina++; render(); };
const bGruppi = document.getElementById('fGruppi');
if (!CARTELLE.length) bGruppi.style.display = 'none';   // report senza dati delle cartelle: niente pulsante
bGruppi.classList.toggle('attivo', raggruppa);
bGruppi.onclick = () => {
  raggruppa = !raggruppa;
  bGruppi.classList.toggle('attivo', raggruppa);
  ordinaLista();
  pagina = 1;
  render();
};

// pagina unica: tutti i risultati in una sola pagina, senza paginazione
const chiediUnica = n => confirm(L.conferma.replace('{n}', n.toLocaleString()));
const bUnica = document.getElementById('fUnica');
bUnica.onclick = () => {
  if (!unica && filtrati.length > SOGLIA_UNICA && !chiediUnica(filtrati.length)) return;
  unica = !unica;
  bUnica.classList.toggle('attivo', unica);
  pagina = 1;
  render();
};

// --- colonne: il pannello elenca tutte le colonne per gruppo (File, Tag musicali, Video, Audio); le caselle
// mostrano o nascondono la colonna subito, senza rigenerare il report. Deve restarne almeno una.
const pCol = document.getElementById('pColonne');
const bCol = document.getElementById('fColonne');
const caselle = new Map();   // id colonna -> casella

function applicaColonne() {
  const idOrd = colOrd >= 0 ? COLS[colOrd].id : null;   // la colonna per cui si sta ordinando
  COLS = TUTTE.filter(c => attive.has(c.id));
  colOrd = idOrd ? COLS.findIndex(c => c.id === idOrd) : -1;
  costruisciIntestazione();
  if (idOrd && colOrd < 0) applicaFiltri();   // la colonna ordinata è sparita: si torna all'ordine di partenza
  else render();                              // altrimenti si resta sulla stessa pagina
}

function cambiaColonna(id, mostra) {
  if (!mostra && attive.size <= 1) { caselle.get(id).checked = true; return; }
  if (mostra) attive.add(id); else attive.delete(id);
  applicaColonne();
}

function impostaColonne(ids) {
  attive.clear();
  ids.forEach(id => attive.add(id));
  caselle.forEach((cb, id) => { cb.checked = attive.has(id); });
  applicaColonne();
}

(function costruisciPannello() {
  const note = new Set(GRUPPI.flatMap(g => g[1]));
  const gruppi = GRUPPI.map(g => [g[0], g[1].slice()]);
  TUTTE.forEach(c => { if (!note.has(c.id)) gruppi[0][1].push(c.id); });   // colonne non previste: nel primo gruppo
  const utili = {gr_video: haVideo, gr_tag: haAudio};   // gruppi che servono solo se nel report ci sono file di quel tipo
  gruppi.forEach(([titolo, ids]) => {
    if (utili[titolo] === false && !ids.some(id => attive.has(id))) return;   // gruppo inutile e nessuna sua colonna in uso
    const box = document.createElement('div');
    box.className = 'pc-gruppo';
    const h = document.createElement('b');
    h.textContent = L[titolo] || titolo;
    box.appendChild(h);
    ids.forEach(id => {
      const etichetta = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = attive.has(id);
      cb.onchange = () => cambiaColonna(id, cb.checked);
      etichetta.appendChild(cb);
      etichetta.appendChild(document.createTextNode(L.nomi_col[id] || id));
      box.appendChild(etichetta);
      caselle.set(id, cb);
    });
    pCol.appendChild(box);
  });
  const azioni = document.createElement('div');
  azioni.className = 'pc-azioni';
  [[L.col_tutte, () => [...caselle.keys()]], [L.col_predef, () => VISIBILI]].forEach(([testo, ids]) => {
    const b = document.createElement('button');
    b.className = 'fbtn';
    b.textContent = testo;
    b.onclick = () => impostaColonne(ids());
    azioni.appendChild(b);
  });
  pCol.appendChild(azioni);
})();
bCol.onclick = () => {
  pCol.hidden = !pCol.hidden;
  bCol.classList.toggle('attivo', !pCol.hidden);
  bCol.setAttribute('aria-expanded', String(!pCol.hidden));
};

// tema chiaro / scuro: il pulsante propone l'altro tema; la scelta resta salvata nel browser
const bTema = document.getElementById('fTema');
const aggiornaTema = () => {
  const chiaro = !!document.documentElement && document.documentElement.getAttribute('data-tema') === 'chiaro';
  bTema.textContent = chiaro ? L.tema_scuro : L.tema_chiaro;
};
bTema.onclick = () => {
  const radice = document.documentElement;
  if (!radice) return;
  const nuovo = radice.getAttribute('data-tema') === 'chiaro' ? 'scuro' : 'chiaro';
  radice.setAttribute('data-tema', nuovo);
  try { localStorage.setItem('mdl-tema-' + ID_REPORT, nuovo); } catch (e) {}   // vale per questo report; senza memoria del browser, solo per questa pagina
  aggiornaTema();
};
aggiornaTema();

// risultati per pagina: 50 / 100 / 500 / 1000. Si resta sui file che si stavano guardando.
const selPP = document.getElementById('fPerPagina');
selPP.onchange = () => {
  const primo = (pagina - 1) * perPagina;       // indice del primo file visibile
  perPagina = Number(selPP.value);
  pagina = Math.floor(primo / perPagina) + 1;
  render();
};

// esportazione CSV: tutte le righe che i filtri lasciano visibili (non solo la pagina corrente), nell'ordine
// scelto e con le colonne mostrate in quel momento; separatore e BOM UTF-8 perché Excel apra bene accenti e colonne
const csvCella = v => {
  let s = String(v == null ? '' : v);
  if (/^[=+\-@\t\r]/.test(s) && s !== '-') s = "'" + s;   // evita che Excel scambi il testo per una formula
  return '"' + s.replace(/"/g, '""') + '"';
};
document.getElementById('fCsv').onclick = () => {
  const sep = L.csv_sep || ';';
  const conCartelle = CARTELLE.length > 0;
  const righe = [(conCartelle ? [L.cartella] : []).concat(COLS.map(c => c.t)).map(csvCella).join(sep)];
  for (const m of vista) {
    const celle = conCartelle ? [CARTELLE[m.k] || L.radice] : [];
    COLS.forEach(c => celle.push(c.show(m)));
    righe.push(celle.map(csvCella).join(sep));
  }
  const blob = new Blob(['\ufeff' + righe.join('\r\n')], {type: 'text/csv;charset=utf-8'});
  const oggi = new Date(), a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `media_report_${oggi.getFullYear()}-${p2(oggi.getMonth() + 1)}-${p2(oggi.getDate())}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
};

// stampa: il layout è nel CSS (@media print); qui si prepara il contenuto
function descrizioneFiltri() {
  const f = [];
  if (filtro.tipo !== 'Tutti') f.push(L.tipi[filtro.tipo] || filtro.tipo);
  if (filtro.hdr) f.push(bHdr.textContent);
  if (filtro.res && selRes.options && selRes.options[selRes.selectedIndex]) f.push(selRes.options[selRes.selectedIndex].text);
  if (filtro.giorni && selData.options && selData.options[selData.selectedIndex]) f.push(selData.options[selData.selectedIndex].text);
  if (filtro.riep) f.push(titoloGruppo(filtro.riep.gruppo) + ': ' + filtro.riep.valore);
  if (filtro.q) f.push('"' + inputCerca.value + '"');
  const n = filtrati.length + (filtrati.length !== DATI.length ? ` ${L.su} ${DATI.length}` : '');
  return (f.length ? `${L.filtri}: ${f.join(' · ')}  —  ` : '') + `${n} ${L.file}`;
}
const bStampa = document.getElementById('fStampa');
bStampa.onclick = () => {
  if (filtrati.length > SOGLIA_UNICA && !confirm(L.conferma_stampa.replace('{n}', filtrati.length.toLocaleString()))) return;
  window.print();
};
if (typeof window !== 'undefined') {   // vale anche per Ctrl+P: prima della stampa si mostrano tutti i risultati
  window.addEventListener('beforeprint', () => {
    document.getElementById('stampaFiltri').textContent = descrizioneFiltri();
    inStampa = true;
    render();
  });
  window.addEventListener('afterprint', () => { inStampa = false; render(); });
}
applicaFiltri();
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="__LANG__"><head><meta charset="UTF-8">
<title>__TITOLO__ - Media Report</title>
<script>var t="__TEMA__";try{var m=localStorage.getItem("mdl-tema-__IDREP__");if(m==="chiaro"||m==="scuro")t=m}catch(e){}document.documentElement.setAttribute("data-tema",t)</script>
<style>__CSS__</style></head>
<body><div class="container">
<h2>🎬 Media Report v__VER__</h2>
<p class="percorso"><strong>__T_R_CARTELLA__</strong> __CARTELLA__</p>
<p><strong>__T_R_GENERATO__</strong> __DATA__ &nbsp;&middot;&nbsp; <strong>ffprobe:</strong> __FFPROBE__</p>
<p><strong>__T_R_TOTALI__</strong> __NFILE__ &nbsp;&middot;&nbsp; <strong>__T_R_N_CARTELLE__</strong> __NCARTELLE__ &nbsp;&middot;&nbsp; <strong>__T_R_SPAZIO__</strong> __SPAZIO__</p>
<div class="riepilogo" id="riepilogo">
  <button class="riep-testa" id="riepTesta" aria-expanded="true" aria-controls="riepCorpo"><span>__T_R_RIEPILOGO__</span><span class="riep-freccia" id="riepFreccia">&#9662;</span></button>
  <p class="riep-tot" id="riepTot"></p>
  <div class="riep-gruppi" id="riepCorpo"></div>
</div>
<p id="stampaFiltri" class="solo-stampa"></p>
<div class="filtri">
  <input type="text" id="cercaInput" placeholder="__T_R_CERCA__">
  <div class="gruppo" id="gTipo">
    <button class="fbtn attivo" data-tipo="Tutti">__T_R_TUTTI__</button>
    <button class="fbtn" data-tipo="Video">__T_R_VIDEO__</button>
    <button class="fbtn" data-tipo="Audio">__T_R_AUDIO__</button>
  </div>
  <button class="fbtn" id="fHdr">__T_R_SOLO_HDR__</button>
  <select id="fRes">
    <option value="">__T_R_RES_QUALSIASI__</option>
    <option value="1280,720">__T_R_RES_720__</option>
    <option value="1920,1080">__T_R_RES_1080__</option>
    <option value="2560,1440">__T_R_RES_1440__</option>
    <option value="3840,2160">__T_R_RES_4K__</option>
  </select>
  <select id="fData">
    <option value="">__T_R_DATA_QUALSIASI__</option>
    <option value="7">__T_R_DATA_7__</option>
    <option value="30">__T_R_DATA_30__</option>
  </select>
  <button class="fbtn" id="fGruppi">__T_R_GRUPPI__</button>
  <button class="fbtn" id="fColonne" aria-controls="pColonne" aria-expanded="false">__T_R_COLONNE__</button>
  <button class="fbtn" id="fReset">__T_R_AZZERA__</button>
  <button class="fbtn" id="fCsv">__T_R_CSV__</button>
  <button class="fbtn" id="fStampa">__T_R_STAMPA__</button>
  <button class="fbtn" id="fTema">__T_R_TEMA__</button>
</div>
<div class="pannello-col" id="pColonne" hidden></div>
<div class="paginazione">
  <button id="btnPrec" class="pag-btn">__T_R_PREC__</button>
  <span id="infoPagina"></span>
  <button id="btnSucc" class="pag-btn">__T_R_SUCC__</button>
  <select id="fPerPagina">
    <option value="50">50 __T_R_PER_PAGINA__</option>
    <option value="100">100 __T_R_PER_PAGINA__</option>
    <option value="500">500 __T_R_PER_PAGINA__</option>
    <option value="1000">1000 __T_R_PER_PAGINA__</option>
  </select>
  <button class="fbtn" id="fUnica">__T_R_UNICA__</button>
</div>
<div class="tabella"><table id="mTable"><thead></thead><tbody></tbody></table></div>
</div>
<script>const ID_REPORT = "__IDREP__"; const DATI = __DATI__; const VISIBILI = __COLONNE__; const L = __LING__; const CARTELLE = __CARTELLE__; const GRUPPI = __GRUPPI__;</script>
<script>__JS__</script>
</body></html>"""


def formatta_dimensione(byte):
    for unita, soglia in (("TB", 1024 ** 4), ("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if byte >= soglia:
            return f"{byte / soglia:.2f} {unita}"
    return f"{byte} B"


def _unc_di_unita(unita):
    r"""Percorso di rete di un disco di rete mappato (Y: -> \\192.168.8.191\Arma Film), oppure None. Solo Windows."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1024)
        lunghezza = ctypes.c_ulong(len(buf))
        if ctypes.windll.mpr.WNetGetConnectionW(unita, buf, ctypes.byref(lunghezza)) == 0 and buf.value:
            return buf.value
    except (OSError, AttributeError, ValueError):
        pass
    return None


def _etichetta_volume(unita):
    """Etichetta del volume di un disco (D: -> Dati), oppure None. Solo Windows."""
    if os.name != "nt":
        return None
    try:
        import ctypes
        etichetta = ctypes.create_unicode_buffer(261)
        if ctypes.windll.kernel32.GetVolumeInformationW(unita + "\\", etichetta, 261, None, None, None, None, 0):
            return etichetta.value or None
    except (OSError, AttributeError, ValueError):
        pass
    return None


def info_cartella(cartella):
    r"""(nome, percorso, percorso di rete) della cartella scansionata, per il report e per il nome del file.

    Il nome è l'ultima cartella del percorso. Una radice non ha un nome di cartella, quindi si usa quello che
    mostra Esplora risorse: la condivisione per \\server\condivisione e per un disco di rete mappato (Y:\ ->
    Arma Film), l'etichetta del volume per un disco locale, altrimenti la lettera dell'unità.
    Il percorso di rete è quello vero di un disco mappato (Y:\Serie -> \\192.168.8.191\Arma Film\Serie); vuoto se non c'è."""
    percorso = os.path.normpath(cartella)
    unita, resto = os.path.splitdrive(percorso)
    unc = _unc_di_unita(unita) if unita and not unita.startswith("\\\\") else None
    rete = os.path.normpath(unc.rstrip("\\") + resto).rstrip("\\") if unc else ""  # senza barra finale (\\server\condivisione)
    nome = os.path.basename(percorso)
    if not nome:  # radice
        if unita.startswith("\\\\"):
            nome = unita.rstrip("\\").split("\\")[-1]
        elif unc:
            nome = unc.rstrip("\\").split("\\")[-1]
        elif unita:
            nome = _etichetta_volume(unita) or unita.rstrip(":")
    return nome or percorso, percorso, rete


def testo_sorgente(cartella):
    r"""Come si scrive la cartella nella casella della sorgente: il percorso e, per un disco di rete mappato, il suo
    percorso di rete tra parentesi (W:\ (\\192.168.8.191\USBDisk1\Music\Flac)). Il testo si può rileggere con
    percorso_da_casella()."""
    _nome, percorso, rete = info_cartella(cartella)
    return percorso + (f" ({rete})" if rete else "")


def percorso_da_casella(testo):
    r"""Il percorso vero contenuto nel testo della casella: toglie l'eventuale « (\\server\condivisione)» finale."""
    return re.sub(r"\s*\(\\\\.*\)\s*$", "", testo.strip())


def nome_file_proposto(cartella):
    """Nome che la finestra di salvataggio propone per il report: quello della cartella scansionata
    (per una radice, come Y:\\, il nome che le dà Esplora risorse; se non c'è nulla di usabile, media_report)."""
    nome, percorso, _rete = info_cartella(cartella)
    if nome == percorso:  # radice senza nome (es. "/"): il percorso non è un nome di file
        nome = ""
    nome = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nome).strip(" .")  # caratteri vietati nei nomi di file
    return (nome or "media_report") + ".html"


_SEGNAPOSTO = re.compile(r"__[A-Z0-9_]+__")


STIMA_MINIMA_MOSTRATA = 10  # secondi: sotto questa soglia la stima non si mostra (a fine scansione sarebbe solo rumore)


class StimaTempo:
    """Quanto manca alla fine dell'analisi, calcolato dal ritmo degli ultimi secondi e non dalla media dall'inizio:
    i file già in cache passano in un istante e falserebbero la media, mentre il ritmo recente segue quello vero
    (se all'inizio ci sono molti file in cache e poi tutti nuovi, la stima si corregge da sola in pochi secondi)."""
    FINESTRA = 10.0  # secondi di storia usati per misurare il ritmo
    MINIMO = 3.0     # secondi dall'inizio prima di cominciare a stimare
    SPAN = 2.0       # secondi di storia necessari per una misura attendibile

    def __init__(self, inizio):
        self.inizio = inizio
        self.campioni = deque()  # (istante, file passati in rassegna)

    def aggiorna(self, n, totale, adesso=None):
        """Registra l'avanzamento e restituisce i secondi stimati, oppure None se non si può ancora dire."""
        adesso = time.perf_counter() if adesso is None else adesso
        self.campioni.append((adesso, n))
        while len(self.campioni) > 2 and adesso - self.campioni[1][0] >= self.FINESTRA:
            self.campioni.popleft()  # si tiene un campione appena più vecchio della finestra
        t0, n0 = self.campioni[0]
        if n >= totale or adesso - self.inizio < self.MINIMO or adesso - t0 < self.SPAN or n <= n0:
            return None
        return (totale - n) / ((n - n0) / (adesso - t0))


def formatta_durata_breve(secondi):
    """«45 s», «3 min», «1 h 05 min». Arrotonda per eccesso: una stima non deve promettere meno del vero."""
    secondi = max(1, math.ceil(secondi))
    if secondi <= 55:
        return f"{(secondi + 4) // 5 * 5} s"  # a passi di 5 secondi
    minuti = math.ceil(secondi / 60)
    if minuti < 60:
        return f"{minuti} min"
    return f"{minuti // 60} h {minuti % 60:02d} min"


def genera_html(cartella, records, colonne, percorso_completo=True, versione_ff=None, lingua="it",
                cartelle=None, n_cartelle=None, tema="scuro", id_report=None):
    if lingua not in TESTI:
        lingua = "it"
    if tema not in TEMI:
        tema = "scuro"  # tema di partenza del report: quello scelto nella finestra del programma
    id_report = id_report or secrets.token_hex(4)  # la scelta fatta nel report si ricorda per ogni report, non per tutti
    tr = lambda chiave: traduci(lingua, chiave)
    nome_cartella, percorso_cartella, rete = info_cartella(cartella)  # nome anche per le radici (es. Y:\ -> Arma Film)
    # intestazione: «nome e percorso» (con il percorso di rete se la cartella sta su un disco mappato) oppure solo il nome
    if percorso_completo and percorso_cartella != nome_cartella:
        nome_mostrato = f"{nome_cartella} \u2014 {percorso_cartella}" + (f" ({rete})" if rete else "")
    elif percorso_completo:
        nome_mostrato = percorso_cartella + (f" ({rete})" if rete else "")
    else:
        nome_mostrato = nome_cartella
    testi = TESTI[lingua]
    per_js = {  # testi usati dal JavaScript del report
        **{k[2:]: v for k, v in testi.items() if k.startswith("j_") and not k.startswith("j_tipo_")},
        "tipi": {"Video": tr("j_tipo_video"), "Audio": tr("j_tipo_audio"), "Generico": tr("j_tipo_generico")},
        "th": {cid: testi.get("th_" + cid) or testi["col_" + cid] for cid in COLONNE},
        "nomi_col": {cid: testi["col_" + cid] for cid in COLONNE},  # nomi completi, per il pannello "Colonne"
    }
    valori = {
        "__LANG__": lingua, "__VER__": VERSIONE, "__CSS__": CSS, "__JS__": JS,
        "__TEMA__": tema, "__IDREP__": id_report,
        "__CARTELLA__": escape(nome_mostrato),
        "__TITOLO__": escape(nome_cartella),  # sempre solo il nome (anche con "percorso completo"): il titolo resta corto
        "__DATA__": datetime.now().strftime(tr("r_formato_data")),
        "__FFPROBE__": escape(versione_ff or tr("versione_nd")),
        "__NFILE__": f"{len(records):,}".replace(",", tr("r_sep_migliaia")),
        "__NCARTELLE__": "-" if n_cartelle is None else f"{n_cartelle:,}".replace(",", tr("r_sep_migliaia")),
        "__SPAZIO__": formatta_dimensione(sum(r["d"] for r in records)),
        # "</" -> "<\/" impedisce a un nome file strano di chiudere il tag <script>
        "__DATI__": json.dumps(records, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"),
        "__COLONNE__": json.dumps(colonne),
        "__GRUPPI__": json.dumps(GRUPPI_COLONNE),  # [[chiave titolo, [colonne]], ...] come nella finestra
        # elenco delle sottocartelle (indice = campo "k" dei record); se c'è, il report si apre raggruppato
        "__CARTELLE__": json.dumps(cartelle or [], ensure_ascii=False).replace("</", "<\\/"),
        "__LING__": json.dumps(per_js, ensure_ascii=False).replace("</", "<\\/"),
        **{f"__T_{k.upper()}__": escape(v) for k, v in testi.items() if k.startswith("r_")},
    }
    # una sola passata sul template: i valori inseriti (anche l'enorme elenco dei file) non vengono
    # riesaminati, quindi niente copie ripetute della stringa e niente sostituzioni accidentali
    return _SEGNAPOSTO.sub(lambda m: valori.get(m.group(0), m.group(0)), TEMPLATE)


# ---------------------------------------------------------------- GUI

# Temi della finestra (coerenti con quelli del report HTML). Ogni colore usato dall'interfaccia sta qui: nessuno
# è scritto altrove, tranne il bianco del testo sopra il colore d'accento. imposta_palette() copia il tema scelto
# nelle variabili globali qui sotto, che applica_stile() e le finestre di dialogo leggono quando vengono costruite.
TEMI = {
    "scuro": {"BG": "#1e1f22", "CARD": "#2b2d31", "CAMPO": "#383a40", "TESTO": "#e6e6e6", "SOTTILE": "#9aa0a6",
              "ACCENT": "#0d6efd", "ACCENT_HOVER": "#3d8bfd", "ERRORE": "#ff6b6b", "OK": "#4cd07d",
              "HOVER": "#4a4d55", "OFF_FG": "#6b6f76", "ACCENT_OFF": "#2a3f66", "ACCENT_OFF_FG": "#8fa6cc",
              "BORDO": "#555555", "LINK": "#3d8bfd", "FG_ATTIVO": "#ffffff"},
    "chiaro": {"BG": "#e9edf2", "CARD": "#ffffff", "CAMPO": "#d9dfe8", "TESTO": "#1f2937", "SOTTILE": "#566072",
               "ACCENT": "#0b5ed7", "ACCENT_HOVER": "#1f6fe5", "ERRORE": "#c92a2a", "OK": "#1d7a33",
               "HOVER": "#c5cdda", "OFF_FG": "#8b95a5", "ACCENT_OFF": "#a9c4ee", "ACCENT_OFF_FG": "#f4f7fc",
               "BORDO": "#bcc5d1", "LINK": "#0b5ed7", "FG_ATTIVO": "#111827"},
}


def imposta_palette(nome):
    """Rende attivo il tema `nome` (uno sconosciuto ripiega sullo scuro)."""
    global BG, CARD, CAMPO, TESTO, SOTTILE, ACCENT, ACCENT_HOVER, ERRORE, OK
    global HOVER, OFF_FG, ACCENT_OFF, ACCENT_OFF_FG, BORDO, LINK, FG_ATTIVO
    p = TEMI.get(nome, TEMI["scuro"])
    BG, CARD, CAMPO, TESTO, SOTTILE = p["BG"], p["CARD"], p["CAMPO"], p["TESTO"], p["SOTTILE"]
    ACCENT, ACCENT_HOVER, ERRORE, OK = p["ACCENT"], p["ACCENT_HOVER"], p["ERRORE"], p["OK"]
    HOVER, OFF_FG, ACCENT_OFF, ACCENT_OFF_FG = p["HOVER"], p["OFF_FG"], p["ACCENT_OFF"], p["ACCENT_OFF_FG"]
    BORDO, LINK, FG_ATTIVO = p["BORDO"], p["LINK"], p["FG_ATTIVO"]


imposta_palette("scuro")
FONT = ("Segoe UI", 10)


def applica_stile(root):
    st = ttk.Style(root)
    st.theme_use("clam")  # il tema ttk più personalizzabile nei colori
    root.configure(bg=BG)

    # elenco a discesa del menu delle cartelle recenti (è un widget tk classico)
    root.option_add("*TCombobox*Listbox.background", CAMPO)
    root.option_add("*TCombobox*Listbox.foreground", TESTO)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.font", FONT)

    st.configure(".", background=BG, foreground=TESTO, font=FONT)
    st.configure("Card.TFrame", background=CARD)
    st.configure("Sezione.TLabel", background=CARD, font=("Segoe UI", 11, "bold"))
    st.configure("Nota.TLabel", background=CARD, foreground=SOTTILE, font=("Segoe UI", 9))
    st.configure("Gruppo.TLabel", background=CARD, foreground=SOTTILE, font=("Segoe UI", 9, "bold"))
    st.configure("Titolo.TLabel", font=("Segoe UI", 18, "bold"))
    st.configure("Sotto.TLabel", foreground=SOTTILE)
    st.configure("Stato.TLabel", foreground=SOTTILE)
    st.configure("Ok.TLabel", foreground=OK, font=("Segoe UI", 10, "bold"))
    st.configure("Errore.TLabel", foreground=ERRORE, font=("Segoe UI", 10, "bold"))
    st.configure("Link.TLabel", foreground=LINK, font=("Segoe UI", 10, "underline"))

    def pulsante(nome, bg, hover, fg, bg_off, fg_off, padding):
        st.configure(nome, background=bg, foreground=fg, bordercolor=bg, lightcolor=bg, darkcolor=bg,
                     focuscolor=bg, padding=padding, relief="flat")
        st.map(nome,
               background=[("disabled", bg_off), ("active", hover)],
               bordercolor=[("disabled", bg_off), ("active", hover)],
               lightcolor=[("disabled", bg_off), ("active", hover)],
               darkcolor=[("disabled", bg_off), ("active", hover)],
               foreground=[("disabled", fg_off)])

    pulsante("TButton", CAMPO, HOVER, TESTO, CARD, OFF_FG, (14, 6))
    st.configure("TMenubutton", background=CAMPO, foreground=TESTO, bordercolor=CAMPO, arrowcolor=TESTO,
                 padding=(14, 6), relief="flat")
    st.map("TMenubutton", background=[("active", HOVER)])
    pulsante("Accent.TButton", ACCENT, ACCENT_HOVER, "#ffffff", ACCENT_OFF, ACCENT_OFF_FG, (22, 10))
    st.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))

    def _fg_su(colore):  # testo bianco o scuro, a seconda della luminosità dello sfondo
        r, g, b = (int(colore[i:i + 2], 16) for i in (1, 3, 5))
        return "#10151c" if (0.299 * r + 0.587 * g + 0.114 * b) > 140 else "#ffffff"

    pulsante("FfOk.TButton", OK, OK, _fg_su(OK), OK, _fg_su(OK), (14, 6))        # ffprobe trovato
    pulsante("FfErr.TButton", ERRORE, ERRORE, _fg_su(ERRORE), ERRORE, _fg_su(ERRORE), (14, 6))  # ffprobe mancante

    st.configure("Card.TCheckbutton", background=CARD, foreground=TESTO, focuscolor=CARD, padding=4,
                 indicatorbackground=CAMPO, indicatorforeground="#ffffff")
    st.map("Card.TCheckbutton",
           background=[("active", CARD)],
           foreground=[("active", FG_ATTIVO)],
           indicatorbackground=[("selected", ACCENT), ("active", HOVER)],
           indicatorforeground=[("selected", "#ffffff")])

    st.configure("Card.TLabel", background=CARD)
    st.configure("Card.TRadiobutton", background=CARD, foreground=TESTO, focuscolor=CARD, padding=4,
                 indicatorbackground=CAMPO, indicatorforeground="#ffffff")
    st.map("Card.TRadiobutton",
           background=[("active", CARD)],
           foreground=[("active", FG_ATTIVO)],
           indicatorbackground=[("selected", ACCENT), ("active", HOVER)],
           indicatorforeground=[("selected", "#ffffff")])

    st.configure("TCombobox", fieldbackground=CAMPO, background=CAMPO, foreground=TESTO,
                 arrowcolor=TESTO, bordercolor=CAMPO, lightcolor=CAMPO, darkcolor=CAMPO, padding=7,
                 selectbackground=ACCENT, selectforeground="#ffffff")
    st.map("TCombobox",
           fieldbackground=[("readonly", CAMPO)], foreground=[("readonly", TESTO)],
           selectbackground=[("readonly", CAMPO)], selectforeground=[("readonly", TESTO)],
           bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)], darkcolor=[("focus", ACCENT)])

    st.configure("Barra.Horizontal.TProgressbar", troughcolor=CAMPO, background=ACCENT,
                 bordercolor=CAMPO, lightcolor=ACCENT, darkcolor=ACCENT, thickness=10)


class App:
    def __init__(self, root):
        self.root = root
        self.ffprobe = None  # lo cerca un thread in background: non ritarda l'apertura della finestra
        self.versione_ff = None
        self.ver_pronta = threading.Event()  # impostato quando ffprobe è stato cercato e la sua versione letta
        self.btn_ffprobe = None
        self.lbl_link = None  # link per scaricare FFmpeg, visibile solo se ffprobe manca
        self.stato = None
        self._larg_testi = 0  # ultima larghezza usata per far andare a capo stato e ffprobe
        self.annulla = threading.Event()
        self.occupato = False
        config = carica_config()
        segna_fase("impostazioni lette")
        self.lingua = config.get("lingua") if config.get("lingua") in LINGUE else "it"
        self.layout = config.get("layout") if config.get("layout") in LAYOUT else "verticale"
        self.tema = config.get("tema") if config.get("tema") in TEMI else "scuro"

        # variabili dell'interfaccia: restano le stesse quando la finestra viene ricostruita (cambio lingua)
        self.recenti = cartelle_recenti(config, controlla=False)
        self.var_cartella = tk.StringVar(value=self.recenti[0] if self.recenti else "")
        salvato = config.get("mostra_cartella")
        self.mostra = tk.StringVar(value=salvato if salvato in ("percorso", "nome") else "percorso")
        self.usa_cache = tk.BooleanVar(value=config.get("usa_cache", True) is not False)
        self.dividi = tk.BooleanVar(value=config.get("dividi_sottocartelle") is True)
        # profili: ognuno ricorda le sue esclusioni e le sue colonne (la casella delle colonne mostra quelle del profilo attivo)
        self.profili, self.profilo_attivo = carica_profili(config)
        self.var_profilo = tk.StringVar(value=self.profilo_attivo)
        attive = self.profili[self.profilo_attivo]["colonne"]
        self.colonne = {cid: tk.BooleanVar(value=cid in attive) for cid in COLONNE}
        self._applica_opzioni_profilo()  # cartella sorgente e opzioni del profilo attivo

        root.title(f"Media Directory Lister v{VERSIONE} by {AUTORE}")
        root.resizable(True, False)  # le dimensioni minime le imposta costruisci(), secondo il layout
        self.var_layout = tk.StringVar(value=self.layout)  # voci del menù «Aspetto»
        self.var_tema = tk.StringVar(value=self.tema)
        imposta_palette(self.tema)
        applica_stile(root)
        self.corpo = None
        self.costruisci()
        segna_fase("interfaccia costruita")
        threading.Thread(target=self._cerca_ffprobe, daemon=True).start()

    def t(self, chiave, **valori):
        return traduci(self.lingua, chiave, **valori)

    def costruisci(self):
        """Crea (o ricrea, dopo un cambio di lingua o di layout) tutti i widget della finestra."""
        ricostruzione = self.corpo is not None
        if ricostruzione:
            self.corpo.destroy()
        t = self.t
        orizzontale = self.layout == "orizzontale"
        self._larg_testi = 0
        corpo = self.corpo = ttk.Frame(self.root, padding=(24, 20))
        corpo.pack(fill="both", expand=True)
        corpo.bind("<Configure>", self._adatta_testi)

        # --- intestazione con i selettori di layout e di lingua
        testa = ttk.Frame(corpo)
        testa.pack(fill="x", pady=(0, 16))
        titoli = ttk.Frame(testa)
        titoli.pack(side="left")
        ttk.Label(titoli, text="Media Directory Lister", style="Titolo.TLabel").pack(anchor="w")
        ttk.Label(titoli, text=t("sottotitolo", v=VERSIONE), style="Sotto.TLabel", justify="left",
                  wraplength=0 if orizzontale else 320).pack(anchor="w")
        destra = ttk.Frame(testa)  # a destra: riga di pulsanti e, sotto «Aspetto», la versione di ffprobe
        destra.pack(side="right", anchor="n")
        self.btn_aspetto = ttk.Menubutton(destra, text=t("aspetto_menu"))
        self.btn_aspetto["menu"] = self._menu_aspetto(self.btn_aspetto)
        self.btn_aspetto.grid(row=0, column=0, sticky="n", padx=(0, 8))
        ttk.Button(destra, text="?", width=3, command=self.apri_contatti).grid(row=0, column=1, sticky="n", padx=(0, 8))
        self.sel_lingua = ttk.Combobox(destra, values=list(LINGUE.values()), state="readonly", width=10)
        self.sel_lingua.set(LINGUE[self.lingua])
        self.sel_lingua.bind("<<ComboboxSelected>>", self.cambia_lingua)
        self.sel_lingua.grid(row=0, column=2, sticky="n")
        testo_ff, stile_ff = self._aspetto_ffprobe()
        self.btn_ffprobe = ttk.Button(destra, text=testo_ff, style=stile_ff, command=self.mostra_info_ffprobe)
        self.btn_ffprobe.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(6, 0))
        self.btn_ffprobe.bind("<Enter>", self._tip_mostra)
        self.btn_ffprobe.bind("<Leave>", self._tip_nascondi)
        self.btn_ffprobe.bind("<Destroy>", self._tip_nascondi)

        # --- parte centrale: verticale = schede una sotto l'altra; orizzontale = cartella e profilo a sinistra,
        # colonne a destra (la finestra è più larga e molto più bassa)
        if orizzontale:
            centro = ttk.Frame(corpo)
            centro.pack(fill="x")
            centro.columnconfigure(1, weight=1)
            sinistra = ttk.Frame(centro)
            sinistra.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
            self._scheda_cartella(sinistra, compatto=True).pack(fill="x")
            card_p = ttk.Frame(sinistra, style="Card.TFrame", padding=16)
            card_p.pack(fill="both", expand=True, pady=(14, 0))
            self._riga_profilo(card_p, compatto=True).pack(fill="x")
            card2 = ttk.Frame(centro, style="Card.TFrame", padding=16)
            card2.grid(row=0, column=1, sticky="nsew")
            self._colonne_report(card2)
        else:
            self._scheda_cartella(corpo, compatto=False).pack(fill="x")
            card2 = ttk.Frame(corpo, style="Card.TFrame", padding=16)
            card2.pack(fill="x", pady=14)
            self._riga_profilo(card2, compatto=False).pack(fill="x", pady=(0, 12))
            self._colonne_report(card2)

        # --- avanzamento e azioni
        self.barra = ttk.Progressbar(corpo, orient="horizontal", mode="determinate",
                                     style="Barra.Horizontal.TProgressbar")
        self.barra.pack(fill="x", pady=(14 if orizzontale else 0, 6))
        self.stato = ttk.Label(corpo, text=t("attesa"), style="Stato.TLabel", wraplength=612, justify="left")
        self.stato.pack(anchor="w")

        azioni = ttk.Frame(corpo)
        azioni.pack(fill="x", pady=(16, 0))
        self.btn_genera = ttk.Button(azioni, text=t("genera"), style="Accent.TButton", command=self.avvia)
        self.btn_genera.pack(side="right")
        self.btn_annulla = ttk.Button(azioni, text=t("annulla"), command=self.annulla.set, state=tk.DISABLED)
        self.btn_annulla.pack(side="right", padx=(0, 10))

        self.lbl_link = ttk.Label(corpo, text=t("scarica_ffmpeg", url=URL_FFMPEG), style="Link.TLabel",
                                  cursor="hand2")
        self.lbl_link.bind("<Button-1>", lambda _evento: self.apri_download_ffmpeg())
        self.aggiorna_stato_ffprobe()

        # dimensioni: il layout verticale resta com'era; quello orizzontale non si stringe sotto la larghezza dei suoi widget
        if orizzontale:
            self.root.update_idletasks()
            self.root.minsize(self.root.winfo_reqwidth(), 300)
        else:
            self.root.minsize(660, 600)
        if ricostruzione:
            self.root.geometry("")  # la finestra riprende la dimensione richiesta dal nuovo layout

    def _adatta_testi(self, evento):
        """Lo stato va a capo alla larghezza della finestra, anche se la si allarga."""
        if evento.widget is not self.corpo or evento.width == self._larg_testi:
            return
        self._larg_testi = evento.width
        spazio = max(300, evento.width - 48)
        try:
            if self.stato is not None:
                self.stato.config(wraplength=spazio)
        except tk.TclError:
            pass  # widget già distrutto (ricostruzione della finestra in corso)

    def _scheda_cartella(self, genitore, compatto):
        """Scheda con la cartella da scansionare e le opzioni. compatto = per la colonna stretta del layout orizzontale."""
        t = self.t
        card1 = ttk.Frame(genitore, style="Card.TFrame", padding=16)
        ttk.Label(card1, text=t("cartella_titolo"), style="Sezione.TLabel").pack(anchor="w", pady=(0, 8))
        riga = ttk.Frame(card1, style="Card.TFrame")
        riga.pack(fill="x")
        self.entry = ttk.Combobox(riga, values=self._valori_recenti(), textvariable=self.var_cartella)
        self.entry.bind("<<ComboboxSelected>>", self._sorgente_scelta)
        self.entry.pack(side="left", fill="x", expand=True)
        ttk.Button(riga, text=t("sfoglia"), command=self.scegli_cartella).pack(side="left", padx=(10, 0))
        ttk.Label(card1, text=t("nota_recenti"), style="Nota.TLabel").pack(anchor="w", pady=(8, 0))

        opzione = ttk.Frame(card1, style="Card.TFrame")
        opzione.pack(fill="x", pady=(10, 0))
        etichetta = ttk.Label(opzione, text=t("mostra_come"), style="Card.TLabel")
        scelte = opzione
        if compatto:  # etichetta sopra, i due pulsanti sotto
            etichetta.pack(anchor="w")
            scelte = ttk.Frame(opzione, style="Card.TFrame")
            scelte.pack(anchor="w", pady=(4, 0))
        else:
            etichetta.pack(side="left")
        ttk.Radiobutton(scelte, text=t("percorso_completo"), variable=self.mostra, value="percorso",
                        style="Card.TRadiobutton").pack(side="left", padx=(0 if compatto else 12, 0))
        ttk.Radiobutton(scelte, text=t("solo_nome"), variable=self.mostra, value="nome",
                        style="Card.TRadiobutton").pack(side="left", padx=(8, 0))

        # layout verticale: «dividi» e «usa la cache» sulla stessa riga (risparmia altezza); compatto: righe separate
        if compatto:
            ttk.Checkbutton(card1, text=t("dividi_sottocartelle"), variable=self.dividi,
                            style="Card.TCheckbutton").pack(anchor="w", pady=(6, 0))
        riga_cache = ttk.Frame(card1, style="Card.TFrame")
        riga_cache.pack(fill="x", pady=(6, 0))
        if not compatto:
            ttk.Checkbutton(riga_cache, text=t("dividi_sottocartelle"), variable=self.dividi,
                            style="Card.TCheckbutton").pack(side="left", padx=(0, 16))
        ttk.Checkbutton(riga_cache, text=t("usa_cache" if compatto else "usa_cache_breve"), variable=self.usa_cache,
                        style="Card.TCheckbutton").pack(side="left")
        bottoni = ttk.Frame(riga_cache, style="Card.TFrame")  # a destra, uno sopra l'altro
        bottoni.pack(side="right")
        ttk.Button(bottoni, text=t("svuota_cronologia"), command=self.svuota_cronologia).pack(anchor="e")
        ttk.Button(bottoni, text=t("svuota_cache"), command=self.svuota_cache).pack(anchor="e", pady=(4, 0))
        return card1

    def _riga_profilo(self, genitore, compatto):
        """Sezione profilo: nome e tipo, esclusioni, gestione. Cartella sorgente, «mostra come», sottocartelle, cache
        e colonne della finestra sono quelle del profilo scelto e cambiano con lui."""
        t = self.t
        riga_p = ttk.Frame(genitore, style="Card.TFrame")
        prima = ttk.Frame(riga_p, style="Card.TFrame")
        prima.pack(fill="x")
        # layout verticale: tutto su una riga sola (risparmia altezza); compatto: esclusioni e Salva vanno sotto
        seconda = ttk.Frame(riga_p, style="Card.TFrame") if compatto else prima
        if compatto:
            seconda.pack(fill="x", pady=(8, 0))
        # un solo menù: elenco dei profili (si sceglie quello attivo) e, sotto, nuovo / rinomina / elimina
        self.btn_profilo = ttk.Menubutton(prima, text=self._testo_profilo(), width=24)
        menu = tk.Menu(self.btn_profilo, tearoff=0, bg=CAMPO, fg=TESTO, activebackground=ACCENT,
                       activeforeground="#ffffff", selectcolor=TESTO, bd=0,
                       postcommand=lambda: self._riempi_menu_profilo(menu))
        self.btn_profilo["menu"] = menu
        self.btn_profilo.pack(side="left")
        ttk.Label(prima, text=t("tipo_etichetta"), style="Card.TLabel").pack(side="left", padx=(14, 0))
        self.combo_tipo = ttk.Combobox(prima, values=[t("tipo_" + tp) for tp in TIPI_PROFILO], state="readonly", width=10)
        self.combo_tipo.set(t("tipo_" + self.profili[self.profilo_attivo]["tipo"]))
        self.combo_tipo.pack(side="left", padx=(8, 0))
        self.combo_tipo.bind("<<ComboboxSelected>>", self.cambia_tipo)
        self.btn_escl = ttk.Button(seconda, text=self.testo_esclusioni(), command=self.modifica_esclusioni)
        self.btn_escl.pack(side="left", padx=(0 if compatto else 14, 0))
        self.btn_salva = ttk.Button(seconda, text=t("profilo_salva"), width=10, command=self.salva_profilo)
        self.btn_salva.pack(side="left", padx=(8, 0))
        ttk.Label(riga_p, text=t("profilo_nota"), style="Nota.TLabel", justify="left",
                  wraplength=420 if compatto else 560).pack(anchor="w", pady=(8, 0))
        return riga_p

    def _testo_profilo(self):
        return f"{self.t('profilo_etichetta')} {self.profilo_attivo}"

    def _riempi_menu_profilo(self, menu):
        """Ricostruisce il menù ogni volta che si apre: profili esistenti, poi le azioni di gestione."""
        menu.delete(0, "end")
        for nome in self.profili:
            menu.add_radiobutton(label=nome, variable=self.var_profilo, value=nome, command=self.cambia_profilo)
        menu.add_separator()
        menu.add_command(label=self.t("profilo_modifica"), command=self.modifica_profilo)
        menu.add_command(label=self.t("profilo_nuovo"), command=self.nuovo_profilo)
        menu.add_command(label=self.t("profilo_rinomina"), command=self.rinomina_profilo)
        menu.add_command(label=self.t("profilo_elimina"), command=self.elimina_profilo)

    def _colonne_report(self, card2):
        """Titolo, Tutte/Nessuna e caselle delle colonne, raggruppate per categoria."""
        t = self.t
        intest = ttk.Frame(card2, style="Card.TFrame")
        intest.pack(fill="x", pady=(0, 6))
        ttk.Label(intest, text=t("colonne_titolo"), style="Sezione.TLabel").pack(side="left")
        ttk.Button(intest, text=t("nessuna"), command=lambda: self.imposta_colonne(False)).pack(side="right")
        ttk.Button(intest, text=t("tutte"), command=lambda: self.imposta_colonne(True)).pack(side="right",
                                                                                              padx=(0, 6))
        griglia = ttk.Frame(card2, style="Card.TFrame")
        griglia.pack(fill="x")
        griglia.columnconfigure(0, minsize=100)  # titoli dei gruppi
        for i in range(1, 4):
            griglia.columnconfigure(i, weight=1, uniform="col")
        raggruppate = {cid for _, cols in GRUPPI_COLONNE for cid in cols}
        gruppi = [(titolo, list(cols)) for titolo, cols in GRUPPI_COLONNE]
        gruppi[0][1].extend(cid for cid in COLONNE if cid not in raggruppate)  # colonne non previste: nel primo gruppo
        riga_g = 0
        for g, (titolo, cols) in enumerate(gruppi):
            ttk.Label(griglia, text=t(titolo), style="Gruppo.TLabel").grid(
                row=riga_g, column=0, sticky="w", padx=(0, 8), pady=(8 if g else 2, 2))
            for n, cid in enumerate(cols):
                ttk.Checkbutton(griglia, text=t("col_" + cid), variable=self.colonne[cid],
                                style="Card.TCheckbutton").grid(row=riga_g + n // 3, column=1 + n % 3, sticky="w",
                                                                pady=(8 if g and n < 3 else 2, 2))
            riga_g += (len(cols) + 2) // 3

    def apri_download_ffmpeg(self):
        try:
            webbrowser.open(URL_FFMPEG)
        except webbrowser.Error:
            pass

    def testo_ffprobe(self):
        """Testo completo su ffprobe (versione e percorso): per il suggerimento al passaggio del mouse e per il clic."""
        if not self.ver_pronta.is_set():
            return "ffprobe: ..."  # ancora in ricerca
        if not self.ffprobe:
            return self.t("ffprobe_mancante")
        ver = self.t("versione_ff", v=self.versione_ff) if self.versione_ff else self.t("versione_nd")
        return f"ffprobe: {ver}\n" + a_capo(self.t("percorso_ff", p=self.ffprobe))

    def _aspetto_ffprobe(self):
        """Scritta breve e stile del pulsante: ✓ verde se ffprobe c'è, ✗ rosso se manca, neutro durante la ricerca."""
        if not self.ver_pronta.is_set():
            return "ffprobe …", "TButton"
        if not self.ffprobe:
            return "ffprobe ✗", "FfErr.TButton"
        return "ffprobe ✓", "FfOk.TButton"

    def mostra_info_ffprobe(self):
        self._tip_nascondi()
        if self.ver_pronta.is_set() and not self.ffprobe:
            messagebox.showwarning("ffprobe", self.testo_ffprobe(), parent=self.root)
        else:
            messagebox.showinfo("ffprobe", self.testo_ffprobe(), parent=self.root)

    def _tip_mostra(self, _evento=None):
        self._tip_nascondi()
        try:
            tip = self._tip = tk.Toplevel(self.root)
            tip.wm_overrideredirect(True)
            x = self.btn_ffprobe.winfo_rootx()
            y = self.btn_ffprobe.winfo_rooty() + self.btn_ffprobe.winfo_height() + 4
            tip.wm_geometry(f"+{x}+{y}")
            tk.Label(tip, text=self.testo_ffprobe(), justify="left", bg=CAMPO, fg=TESTO, font=FONT,
                     bd=1, relief="solid", padx=8, pady=5).pack()
        except tk.TclError:
            self._tip = None

    def _tip_nascondi(self, _evento=None):
        tip = getattr(self, "_tip", None)
        self._tip = None
        if tip is not None:
            try:
                tip.destroy()
            except tk.TclError:
                pass

    def _cerca_ffprobe(self):
        """Thread in background: cerca ffprobe e ne legge la versione (operazioni che possono essere lente)."""
        self.ffprobe = trova_ffprobe()
        segna_fase("ffprobe cercato: " + (self.ffprobe or "non trovato"))
        self.versione_ff = versione_ffprobe(self.ffprobe)
        segna_fase("versione di ffprobe letta: " + str(self.versione_ff))
        self.ver_pronta.set()
        salva_log_avvio()
        try:
            self.root.after(0, self.aggiorna_stato_ffprobe)
        except Exception:
            pass  # finestra già chiusa

    def aggiorna_stato_ffprobe(self):
        """Adegua etichetta, pulsante e messaggio a quanto si sa di ffprobe: in ricerca, trovato o mancante."""
        if self.btn_ffprobe is not None:
            testo_ff, stile_ff = self._aspetto_ffprobe()
            self.btn_ffprobe.config(text=testo_ff, style=stile_ff)
        if self.lbl_link is not None:  # il link compare solo quando la ricerca è finita e ffprobe non c'è
            if self.ver_pronta.is_set() and not self.ffprobe:
                self.lbl_link.pack(anchor="w", pady=(4, 0), after=self.stato)
            else:
                self.lbl_link.pack_forget()
        if self.occupato:
            return
        if not self.ver_pronta.is_set():
            self.btn_genera.config(state=tk.DISABLED)  # si può generare solo quando ffprobe è noto
        elif self.ffprobe:
            self.btn_genera.config(state=tk.NORMAL)
        else:
            self.btn_genera.config(state=tk.DISABLED)
            self.stato.config(text=self.t("ffprobe_mancante"), style="Errore.TLabel")

    def cambia_lingua(self, _evento=None):
        scelta = next((c for c, nome in LINGUE.items() if nome == self.sel_lingua.get()), self.lingua)
        if scelta == self.lingua or self.occupato:
            return
        self.lingua = scelta
        config = carica_config()
        config["lingua"] = scelta
        salva_config(config)
        # dopo l'evento: un widget non va distrutto dentro il proprio callback
        self.root.after(0, self.costruisci)

    def _menu_aspetto(self, genitore):
        """Menù «Aspetto»: layout della finestra (verticale / orizzontale) e tema (scuro / chiaro)."""
        menu = tk.Menu(genitore, tearoff=0, bg=CAMPO, fg=TESTO, activebackground=ACCENT,
                       activeforeground="#ffffff", bd=0)
        for nome in LAYOUT:
            menu.add_radiobutton(label=self.t("layout_" + nome), variable=self.var_layout, value=nome,
                                 command=lambda n=nome: self.cambia_layout(n))
        menu.add_separator()
        for nome in TEMI:
            menu.add_radiobutton(label=self.t("tema_" + nome), variable=self.var_tema, value=nome,
                                 command=lambda n=nome: self.cambia_tema(n))
        return menu

    def cambia_layout(self, scelta):
        if scelta == self.layout or self.occupato:
            self.var_layout.set(self.layout)  # durante la scansione resta quello attuale
            return
        self.layout = scelta
        self.var_layout.set(scelta)  # il segno di spunta nel menù segue sempre la scelta effettiva
        config = carica_config()
        config["layout"] = scelta
        salva_config(config)
        self.root.after(0, self.costruisci)  # dopo l'evento: un widget non va distrutto dentro il proprio callback

    def cambia_tema(self, scelta):
        if scelta == self.tema or self.occupato:
            self.var_tema.set(self.tema)
            return
        self.tema = scelta
        self.var_tema.set(scelta)
        config = carica_config()
        config["tema"] = scelta
        salva_config(config)
        imposta_palette(scelta)
        applica_stile(self.root)  # ricolora gli stili ttk; i widget si ricreano con i colori nuovi
        self.root.after(0, self.costruisci)

    # --- profili
    def _sorgente(self):
        """La cartella sorgente scritta nella casella, senza l'eventuale percorso di rete tra parentesi."""
        return percorso_da_casella(self.var_cartella.get())

    def _valori_recenti(self):
        return [testo_sorgente(c) for c in self.recenti]

    def _sorgente_scelta(self, _evento=None):
        """Scelta una cartella recente: si scrive con il suo percorso completo."""
        self.var_cartella.set(testo_sorgente(self._sorgente()))

    def _colonne_scelte(self):
        return [cid for cid in COLONNE if self.colonne[cid].get()]

    def _memorizza_colonne(self):
        """Tutto ciò che si imposta nella finestra appartiene al profilo attivo e si salva lì: colonne spuntate (se non
        ne resta nessuna, restano le vecchie), cartella sorgente, «mostra come», sottocartelle e cache."""
        profilo = self.profili[self.profilo_attivo]
        scelte = self._colonne_scelte()
        if scelte:
            profilo["colonne"] = scelte
        profilo["sorgente"] = self._sorgente()
        profilo["mostra"] = self.mostra.get()
        profilo["dividi"] = bool(self.dividi.get())
        profilo["usa_cache"] = bool(self.usa_cache.get())

    def _applica_colonne_profilo(self):
        attive = self.profili[self.profilo_attivo]["colonne"]
        for cid, var in self.colonne.items():
            var.set(cid in attive)

    def _applica_opzioni_profilo(self, svuota_sorgente=False):
        """Mette nella finestra cartella sorgente e opzioni del profilo attivo. Se il profilo non ha una sorgente la
        casella resta com'è, tranne con svuota_sorgente (cambio di profilo): così non si genera il report sulla
        cartella dell'altro profilo."""
        profilo = self.profili[self.profilo_attivo]
        if profilo["sorgente"]:
            self.var_cartella.set(testo_sorgente(profilo["sorgente"]))
        elif svuota_sorgente:
            self.var_cartella.set("")
        self.mostra.set(profilo["mostra"])
        self.dividi.set(profilo["dividi"])
        self.usa_cache.set(profilo["usa_cache"])

    def _salva_profili(self):
        config = carica_config()
        config["profili"] = self.profili
        config["profilo_attivo"] = self.profilo_attivo
        config["migrazione_3_9g"] = True
        config["migrazione_3_9t"] = True
        config.pop("colonne", None)  # ora le colonne stanno nei profili
        salva_config(config)

    def _esclusioni_attive(self):
        profilo = self.profili[self.profilo_attivo]
        return set(profilo["estensioni_escluse"]), set(profilo["nomi_esclusi"])

    def testo_esclusioni(self):
        profilo = self.profili[self.profilo_attivo]
        return self.t("escl_bottone", n=len(profilo["estensioni_escluse"]) + len(profilo["nomi_esclusi"]))

    def _profilo_cambiato(self, svuota_sorgente=False):
        """Allinea finestra e file di configurazione dopo un cambio, un inserimento o una cancellazione di profilo."""
        self.var_profilo.set(self.profilo_attivo)
        self.btn_profilo.config(text=self._testo_profilo())
        self._applica_colonne_profilo()
        self._applica_opzioni_profilo(svuota_sorgente)
        self.combo_tipo.set(self.t("tipo_" + self.profili[self.profilo_attivo]["tipo"]))
        self.btn_escl.config(text=self.testo_esclusioni())
        self._salva_profili()

    def cambia_profilo(self, _evento=None):
        nuovo = self.var_profilo.get()
        if self.occupato or nuovo == self.profilo_attivo or nuovo not in self.profili:
            self.var_profilo.set(self.profilo_attivo)
            return
        self._memorizza_colonne()  # le colonne modificate restano nel profilo che si lascia
        self.profilo_attivo = nuovo
        self._profilo_cambiato(svuota_sorgente=True)  # la casella mostra la cartella del nuovo profilo

    def salva_profilo(self):
        """Salva subito nel profilo attivo cartella, tipo, colonne, esclusioni e opzioni che si vedono nella finestra."""
        if self.occupato:
            return
        self._memorizza_colonne()
        self._salva_profili()
        self.stato.config(text=self.t("profilo_salvato", nome=self.profilo_attivo), style="Ok.TLabel")
        # la riga di stato sta in fondo e può non vedersi: la conferma compare anche sul pulsante stesso
        if getattr(self, "_id_conferma", None):
            self.root.after_cancel(self._id_conferma)
        self.btn_salva.config(text=self.t("profilo_salvato_breve"))
        self._id_conferma = self.root.after(2000, self._ripristina_salva)

    def _ripristina_salva(self):
        self._id_conferma = None
        try:
            self.btn_salva.config(text=self.t("profilo_salva"))
        except tk.TclError:
            pass  # finestra ricostruita nel frattempo (cambio lingua o layout)

    def nuovo_profilo(self):
        """Finestra per creare un profilo (es. Animazione): nome e tipo; le colonne partono da quelle predefinite del
        tipo oppure da una copia di quelle attuali. Cartella, esclusioni e opzioni attuali si copiano."""
        if self.occupato:
            return
        t = self.t
        fin = tk.Toplevel(self.root)
        fin.title(t("nuovo_titolo"))
        fin.configure(bg=BG)
        fin.transient(self.root)
        fin.resizable(False, False)
        corpo = ttk.Frame(fin, padding=20)
        corpo.pack(fill="both", expand=True)
        var_nome = tk.StringVar(value="")
        var_tipo = tk.StringVar(value=t("tipo_" + self.profili[self.profilo_attivo]["tipo"]))
        var_modello = tk.BooleanVar(value=True)

        ttk.Label(corpo, text=t("nuovo_nome"), style="Sezione.TLabel").pack(anchor="w", pady=(0, 6))
        campo = tk.Entry(corpo, textvariable=var_nome, width=44, bg=CAMPO, fg=TESTO, insertbackground=TESTO,
                         relief="flat", font=FONT, highlightthickness=1, highlightbackground=BORDO, highlightcolor=ACCENT)
        campo.pack(fill="x", pady=(0, 14), ipady=4)
        riga_tipo = ttk.Frame(corpo)
        riga_tipo.pack(fill="x", pady=(0, 8))
        ttk.Label(riga_tipo, text=t("nuovo_tipo"), style="Sezione.TLabel").pack(side="left")
        ttk.Combobox(riga_tipo, values=[t("tipo_" + tp) for tp in TIPI_PROFILO], textvariable=var_tipo,
                     state="readonly", width=12).pack(side="left", padx=(10, 0))
        ttk.Checkbutton(corpo, text=t("nuovo_modello"), variable=var_modello).pack(anchor="w", pady=(0, 8))
        ttk.Label(corpo, text=t("nuovo_nota"), style="Nota.TLabel", wraplength=420, justify="left").pack(anchor="w", pady=(0, 10))
        errore = ttk.Label(corpo, text="", style="Errore.TLabel", wraplength=420, justify="left")
        errore.pack(anchor="w", pady=(0, 8))

        def crea(_evento=None):
            nome = var_nome.get().strip()
            chiave = errore_nome_profilo(nome, self.profili)
            if chiave:
                errore.config(text=t(chiave, nome=nome))
                return
            tipo = next((tp for tp in TIPI_PROFILO if t("tipo_" + tp) == var_tipo.get()), "generale")
            self._memorizza_colonne()
            nuovo = copy.deepcopy(self.profili[self.profilo_attivo])  # cartella, esclusioni, opzioni, colonne attuali
            nuovo["tipo"] = tipo
            if var_modello.get():
                modello = set(COLONNE_PER_TIPO[tipo])
                nuovo["colonne"] = [c for c in COLONNE if c in modello]
            self.profili[nome] = nuovo
            self.profilo_attivo = nome
            fin.destroy()
            self._profilo_cambiato()

        azioni = ttk.Frame(corpo)
        azioni.pack(fill="x")
        ttk.Button(azioni, text=t("nuovo_crea"), style="Accent.TButton", command=crea).pack(side="right")
        ttk.Button(azioni, text=t("annulla"), command=fin.destroy).pack(side="right", padx=(0, 10))
        campo.bind("<Return>", crea)
        campo.focus_set()
        fin.grab_set()

    def modifica_profilo(self):
        """Finestra per modificare il profilo attivo: nome, cartella sorgente (il percorso) e tipo."""
        if self.occupato:
            return
        t = self.t
        vecchio = self.profilo_attivo
        profilo = self.profili[vecchio]
        fin = tk.Toplevel(self.root)
        fin.title(t("modifica_titolo"))
        fin.configure(bg=BG)
        fin.transient(self.root)
        fin.resizable(False, False)
        corpo = ttk.Frame(fin, padding=20)
        corpo.pack(fill="both", expand=True)
        var_nome = tk.StringVar(value=vecchio)
        var_cartella = tk.StringVar(value=testo_sorgente(profilo["sorgente"]) if profilo["sorgente"] else "")
        var_tipo = tk.StringVar(value=t("tipo_" + profilo["tipo"]))

        def campo_testo(genitore, variabile, **opzioni):
            return tk.Entry(genitore, textvariable=variabile, bg=CAMPO, fg=TESTO, insertbackground=TESTO,
                            relief="flat", font=FONT, highlightthickness=1, highlightbackground=BORDO,
                            highlightcolor=ACCENT, **opzioni)

        ttk.Label(corpo, text=t("modifica_nome"), style="Sezione.TLabel").pack(anchor="w", pady=(0, 6))
        campo_nome = campo_testo(corpo, var_nome, width=52)
        campo_nome.pack(fill="x", pady=(0, 14), ipady=4)
        ttk.Label(corpo, text=t("modifica_cartella"), style="Sezione.TLabel").pack(anchor="w", pady=(0, 6))
        riga_c = ttk.Frame(corpo)
        riga_c.pack(fill="x", pady=(0, 14))
        campo_testo(riga_c, var_cartella).pack(side="left", fill="x", expand=True, ipady=4)

        def sfoglia():
            opzioni = {"parent": fin}
            attuale = percorso_da_casella(var_cartella.get())
            if attuale and os.path.isdir(attuale):
                opzioni["initialdir"] = attuale
            scelta = filedialog.askdirectory(**opzioni)
            if scelta:
                var_cartella.set(testo_sorgente(scelta))

        ttk.Button(riga_c, text=t("sfoglia"), command=sfoglia).pack(side="left", padx=(10, 0))
        riga_tipo = ttk.Frame(corpo)
        riga_tipo.pack(fill="x", pady=(0, 10))
        ttk.Label(riga_tipo, text=t("nuovo_tipo"), style="Sezione.TLabel").pack(side="left")
        ttk.Combobox(riga_tipo, values=[t("tipo_" + tp) for tp in TIPI_PROFILO], textvariable=var_tipo,
                     state="readonly", width=12).pack(side="left", padx=(10, 0))
        errore = ttk.Label(corpo, text="", style="Errore.TLabel", wraplength=480, justify="left")
        errore.pack(anchor="w", pady=(0, 8))

        def applica(_evento=None):
            nome = var_nome.get().strip()
            chiave = errore_nome_profilo(nome, self.profili, ignora=vecchio)
            if chiave:
                errore.config(text=t(chiave, nome=nome))
                return
            cartella = percorso_da_casella(var_cartella.get())
            if cartella and not os.path.isdir(cartella):
                errore.config(text=t("cartella_non_valida"))
                return
            tipo = next((tp for tp in TIPI_PROFILO if t("tipo_" + tp) == var_tipo.get()), profilo["tipo"])
            tipo_cambiato = tipo != profilo["tipo"]
            self._memorizza_colonne()  # le colonne modificate nella finestra restano nel profilo
            profilo["sorgente"] = os.path.abspath(cartella) if cartella else ""
            profilo["tipo"] = tipo
            if nome != vecchio:
                self.profili = {(nome if k == vecchio else k): v for k, v in self.profili.items()}  # stessa posizione
                self.profilo_attivo = nome
            fin.destroy()
            if tipo_cambiato and messagebox.askyesno(t("tipo_titolo"), t("tipo_testo", tipo=t("tipo_" + tipo))):
                modello = set(COLONNE_PER_TIPO[tipo])
                profilo["colonne"] = [c for c in COLONNE if c in modello]
            self._profilo_cambiato(svuota_sorgente=True)  # la casella della cartella mostra quella del profilo

        azioni = ttk.Frame(corpo)
        azioni.pack(fill="x")
        ttk.Button(azioni, text=t("profilo_salva"), style="Accent.TButton", command=applica).pack(side="right")
        ttk.Button(azioni, text=t("annulla"), command=fin.destroy).pack(side="right", padx=(0, 10))
        campo_nome.bind("<Return>", applica)
        campo_nome.focus_set()
        fin.grab_set()

    def cambia_tipo(self, _evento=None):
        """Cambia il tipo del profilo attivo; chiede se applicare anche le colonne predefinite del nuovo tipo."""
        profilo = self.profili[self.profilo_attivo]
        scelto = next((tp for tp in TIPI_PROFILO if self.t("tipo_" + tp) == self.combo_tipo.get()), profilo["tipo"])
        if self.occupato or scelto == profilo["tipo"]:
            self.combo_tipo.set(self.t("tipo_" + profilo["tipo"]))
            return
        self._memorizza_colonne()
        profilo["tipo"] = scelto
        if messagebox.askyesno(self.t("tipo_titolo"), self.t("tipo_testo", tipo=self.t("tipo_" + scelto))):
            modello = set(COLONNE_PER_TIPO[scelto])
            profilo["colonne"] = [c for c in COLONNE if c in modello]
            self._applica_colonne_profilo()
        self._salva_profili()

    def rinomina_profilo(self):
        if self.occupato:
            return
        vecchio = self.profilo_attivo
        nome = simpledialog.askstring(self.t("rinomina_titolo"), self.t("rinomina_testo", nome=vecchio),
                                      initialvalue=vecchio, parent=self.root)
        if nome is None:
            return
        nome = nome.strip()
        if nome == vecchio:
            return
        errore = errore_nome_profilo(nome, self.profili, ignora=vecchio)
        if errore:
            messagebox.showerror(self.t("errore"), self.t(errore, nome=nome))
            return
        self._memorizza_colonne()
        self.profili = {(nome if k == vecchio else k): v for k, v in self.profili.items()}  # stessa posizione nell'elenco
        self.profilo_attivo = nome
        self._profilo_cambiato()

    def elimina_profilo(self):
        if self.occupato:
            return
        ultimo = len(self.profili) <= 1
        testo = "elimina_ultimo_testo" if ultimo else "elimina_testo"  # il programma ha sempre un profilo: l'ultimo si sostituisce
        if not messagebox.askyesno(self.t("elimina_titolo"), self.t(testo, nome=self.profilo_attivo)):
            return
        if ultimo:
            self.profili = {"Generale": profili_predefiniti()["Generale"]}
            self.profilo_attivo = "Generale"
        else:
            del self.profili[self.profilo_attivo]
            self.profilo_attivo = "Generale" if "Generale" in self.profili else next(iter(self.profili))
        self._profilo_cambiato(svuota_sorgente=not ultimo)

    def _applica_esclusioni(self, testo_estensioni, testo_nomi):
        """Salva nel profilo attivo le esclusioni scritte nella finestra. Restituisce le voci non valide, ignorate."""
        scartate = []
        profilo = self.profili[self.profilo_attivo]
        profilo["estensioni_escluse"] = normalizza_estensioni(testo_estensioni, scartate)
        profilo["nomi_esclusi"] = normalizza_nomi(testo_nomi, scartate)
        self._memorizza_colonne()
        self._salva_profili()
        self.btn_escl.config(text=self.testo_esclusioni())
        return scartate

    def modifica_esclusioni(self):
        """Finestra per modificare le estensioni e i nomi di file esclusi dal profilo attivo."""
        if self.occupato:
            return
        t = self.t
        profilo = self.profili[self.profilo_attivo]
        fin = tk.Toplevel(self.root)
        fin.title(t("escl_titolo", nome=self.profilo_attivo))
        fin.configure(bg=BG)
        fin.transient(self.root)
        fin.resizable(False, False)
        corpo = ttk.Frame(fin, padding=20)
        corpo.pack(fill="both", expand=True)

        def casella(titolo, nota, contenuto, righe):
            ttk.Label(corpo, text=titolo, style="Sezione.TLabel").pack(anchor="w", pady=(0, 2))
            ttk.Label(corpo, text=nota, style="Sotto.TLabel", wraplength=520, justify="left").pack(anchor="w", pady=(0, 6))
            c = tk.Text(corpo, width=64, height=righe, wrap="word", bg=CAMPO, fg=TESTO, insertbackground=TESTO,
                        relief="flat", font=FONT, highlightthickness=1, highlightbackground=BORDO,
                        highlightcolor=ACCENT, padx=8, pady=6)
            c.insert("1.0", contenuto)
            c.pack(fill="x", pady=(0, 14))
            return c

        txt_est = casella(t("escl_estensioni"), t("escl_estensioni_nota"), " ".join(profilo["estensioni_escluse"]), 5)
        txt_nomi = casella(t("escl_nomi"), t("escl_nomi_nota"), "\n".join(profilo["nomi_esclusi"]), 4)

        def ripristina():
            for campo, valore in ((txt_est, " ".join(sorted(ESTENSIONI_ESCLUSE))), (txt_nomi, "\n".join(sorted(NOMI_ESCLUSI)))):
                campo.delete("1.0", "end")
                campo.insert("1.0", valore)

        def salva():
            scartate = self._applica_esclusioni(txt_est.get("1.0", "end"), txt_nomi.get("1.0", "end"))
            fin.destroy()
            if scartate:
                messagebox.showinfo(t("info"), t("escl_ignorate", voci=", ".join(scartate)))

        azioni = ttk.Frame(corpo)
        azioni.pack(fill="x")
        ttk.Button(azioni, text=t("escl_ripristina"), command=ripristina).pack(side="left")
        ttk.Button(azioni, text=t("escl_salva"), style="Accent.TButton", command=salva).pack(side="right")
        ttk.Button(azioni, text=t("annulla"), command=fin.destroy).pack(side="right", padx=(0, 10))
        fin.grab_set()

    # --- contatti
    def scrivi_email(self):
        """Apre il programma di posta con l'indirizzo e un oggetto già pronti (con la versione, utile per le segnalazioni)."""
        oggetto = quote(f"Media Directory Lister v{VERSIONE}")
        try:
            webbrowser.open(f"mailto:{EMAIL_CONTATTI}?subject={oggetto}")
        except webbrowser.Error:
            pass

    def apri_contatti(self):
        """Finestrella del pulsante «?»: invito a scrivere (suggerimenti, richieste, segnalazioni) con l'email cliccabile."""
        t = self.t
        fin = tk.Toplevel(self.root)
        fin.title(t("contatti_titolo"))
        fin.configure(bg=BG)
        fin.transient(self.root)
        fin.resizable(False, False)
        corpo = ttk.Frame(fin, padding=24)
        corpo.pack(fill="both", expand=True)
        ttk.Label(corpo, text=t("contatti_testo"), wraplength=420, justify="left").pack(anchor="w")
        ttk.Label(corpo, text=t("contatti_email_intro"), wraplength=420, justify="left").pack(anchor="w", pady=(14, 2))
        link = ttk.Label(corpo, text=EMAIL_CONTATTI, style="Link.TLabel", cursor="hand2")
        link.pack(anchor="w")
        link.bind("<Button-1>", lambda _evento: self.scrivi_email())
        ttk.Button(corpo, text=t("chiudi"), command=fin.destroy).pack(anchor="e", pady=(18, 0))
        fin.grab_set()

    def imposta_colonne(self, valore):
        for var in self.colonne.values():
            var.set(valore)

    def svuota_cronologia(self):
        """Svuota l'elenco delle cartelle recenti del menu a tendina; la cartella scritta nella casella e quelle
        salvate nei profili restano dove sono."""
        if self.occupato:
            return
        if not messagebox.askyesno(self.t("cronologia_titolo"), self.t("cronologia_conferma")):
            return
        config = carica_config()
        config["cartelle_recenti"] = []
        config.pop("cartella_scansione", None)
        salva_config(config)
        self.recenti = []
        self.entry["values"] = []
        messagebox.showinfo(self.t("cronologia_titolo"), self.t("cronologia_svuotata"))

    def svuota_cache(self):
        try:
            if svuota_cache_su_disco():
                messagebox.showinfo(self.t("cache_titolo"), self.t("cache_svuotata"))
            else:
                messagebox.showinfo(self.t("cache_titolo"), self.t("cache_gia_vuota"))
        except OSError as e:
            messagebox.showerror(self.t("errore"), self.t("cache_errore", errore=e))

    def scegli_cartella(self):
        opzioni = {}
        attuale = self._sorgente()
        if os.path.isdir(attuale):
            opzioni["initialdir"] = attuale
        c = filedialog.askdirectory(**opzioni)
        if c:
            self.var_cartella.set(testo_sorgente(c))

    def avvia(self):
        if not self._sorgente():  # casella vuota: abspath("") sarebbe la cartella di lavoro corrente
            messagebox.showerror(self.t("errore"), self.t("cartella_non_valida"))
            return
        cartella = os.path.abspath(self._sorgente())
        if not os.path.isdir(cartella):
            messagebox.showerror(self.t("errore"), self.t("cartella_non_valida"))
            return
        scelte = [cid for cid in COLONNE if self.colonne[cid].get()]
        if not scelte:
            messagebox.showerror(self.t("errore"), self.t("nessuna_colonna"))
            return
        config = carica_config()
        recenti = [cartella] + [c for c in cartelle_recenti(config, controlla=False)
                                if os.path.normcase(c) != os.path.normcase(cartella)]
        recenti = recenti[:MAX_RECENTI]
        config.pop("cartella_scansione", None)
        self.var_cartella.set(testo_sorgente(cartella))  # percorso normalizzato e completo (con il percorso di rete, se c'è)
        self._memorizza_colonne()  # colonne, cartella sorgente e opzioni si salvano nel profilo attivo
        config.update(cartelle_recenti=recenti, mostra_cartella=self.mostra.get(), usa_cache=self.usa_cache.get(),
                      dividi_sottocartelle=self.dividi.get(), profili=self.profili, profilo_attivo=self.profilo_attivo,
                      migrazione_3_9g=True, migrazione_3_9t=True)
        config.pop("colonne", None)
        self.recenti = recenti
        self.entry["values"] = self._valori_recenti()
        salva_config(config)
        opzioni = {"defaultextension": ".html", "filetypes": [("HTML", "*.html")], "title": self.t("salva_titolo"),
                   "initialfile": nome_file_proposto(cartella)}  # propone il nome della cartella scansionata
        ultima = config.get("cartella_salvataggio", "")
        if os.path.isdir(ultima):
            opzioni["initialdir"] = ultima  # riparte dall'ultima cartella usata per salvare
        out = filedialog.asksaveasfilename(**opzioni)
        if not out:
            return
        self.annulla.clear()
        self.occupato = True
        self.sel_lingua.config(state="disabled")  # durante la scansione la lingua non si cambia
        self.btn_aspetto.config(state="disabled")  # e nemmeno layout e tema
        self.btn_genera.config(state=tk.DISABLED)
        self.btn_annulla.config(state=tk.NORMAL)
        self.barra["value"] = 0
        self.stato.config(text=self.t("ricerca_file"), style="Stato.TLabel")
        threading.Thread(target=self.lavora, daemon=True,
                         args=(cartella, out, scelte, self.mostra.get(), self.usa_cache.get(),
                               self.dividi.get(), self._esclusioni_attive())).start()

    # --- thread di lavoro (non tocca mai direttamente i widget)
    def lavora(self, cartella, out, colonne, mostra, usa_cache=True, dividi=False, esclusioni=None):
        try:
            self._lavora(cartella, out, colonne, mostra, usa_cache, dividi, esclusioni)
        except Exception as e:  # qualsiasi imprevisto: l'interfaccia non deve restare bloccata
            self.root.after(0, self.fine, self.t("errore_imprevisto", errore=e), True)

    def _lavora(self, cartella, out, colonne, mostra, usa_cache=True, dividi=False, esclusioni=None):
        t_inizio = time.perf_counter()
        statistiche = {}
        estensioni, nomi = esclusioni if esclusioni else (None, None)  # None = esclusioni predefinite
        files = elenca_file(cartella, statistiche, estensioni, nomi, self.annulla, self._avanza_ricerca)
        if files is None:  # annullata durante la ricerca dei file
            self.root.after(0, self.fine, self.t("annullata"), False)
            return
        t_elenco = time.perf_counter()
        totale = len(files)
        if totale == 0:
            self.root.after(0, self.fine, self.t("cartella_vuota"), False)
            return

        self.ver_pronta.wait(120)  # serve per la cache e per il report (di solito è già pronta)
        cache = None
        if usa_cache and self.ffprobe:
            cache = CacheScansioni(self.versione_ff)
            cache.carica(cartella)

        records, cartelle, indici = [], [], {}
        stima = StimaTempo(t_elenco)
        workers = min(8, (os.cpu_count() or 2) * 2)  # ffprobe è I/O bound: più thread = molto più veloce
        with ThreadPoolExecutor(max_workers=workers) as ex:
            risultati = ex.map(lambda f: analizza(f[0], self.ffprobe, self.annulla, f[1], cache, f[2]), files)
            for n, rec in enumerate(risultati, 1):
                if rec:
                    if dividi:  # sottocartella (relativa) del file: i record portano solo il suo indice "k"
                        rel = os.path.dirname(files[n - 1][0])[len(cartella):].strip(os.sep)
                        if rel not in indici:
                            indici[rel] = len(cartelle)
                            cartelle.append(rel)
                        rec = {**rec, "k": indici[rel]}  # copia: il record potrebbe essere quello della cache
                    records.append(rec)
                if n % 10 == 0 or n == totale:  # aggiorna la GUI ogni 10 file, non a ogni file
                    self.root.after(0, self.progresso, n, totale, stima.aggiorna(n, totale))

        t_analisi = time.perf_counter()
        if cache:  # salvata subito, anche se poi il report non si scrive: il lavoro fatto non va perso
            cache.salva(cartella, pota=not self.annulla.is_set())
        if self.annulla.is_set():
            self.root.after(0, self.fine, self.t("annullata"), False)
            return
        try:
            # errors="replace": un nome file con caratteri non codificabili non deve far fallire il salvataggio
            with open(out, "w", encoding="utf-8", errors="replace") as f:
                f.write(genera_html(cartella, records, colonne, mostra == "percorso", self.versione_ff,
                                    self.lingua, cartelle if len(cartelle) > 1 else None, statistiche.get("cartelle"),
                                    tema=self.tema))
        except OSError as e:
            self.root.after(0, self.fine, self.t("salvataggio_fallito", errore=e), True)
            return
        dettaglio = ""
        if cache and (cache.dalla_cache or cache.analizzati):
            dettaglio = self.t("dettaglio_cache", h=cache.dalla_cache, a=cache.analizzati)
        dettaglio += self.t("tempi", a=f"{t_elenco - t_inizio:.1f}", b=f"{t_analisi - t_elenco:.1f}",
                            c=f"{time.perf_counter() - t_analisi:.1f}")
        self.root.after(0, self.fine, self.t("report_salvato"), False, True, out, dettaglio)

    def _avanza_ricerca(self, n):
        """Chiamata dal thread di lavoro durante la ricerca dei file: l'aggiornamento della finestra passa dal thread principale."""
        try:
            self.root.after(0, self.progresso_ricerca, n)
        except Exception:
            pass  # finestra già chiusa

    def progresso_ricerca(self, n):
        if self.occupato and not self.annulla.is_set():
            self.stato.config(text=self.t("ricerca_file_n", n=n))

    def progresso(self, n, totale, stima=None):
        pct = int(n / totale * 100)
        self.barra["value"] = pct
        if stima is None or stima < STIMA_MINIMA_MOSTRATA:  # troppo presto per stimare, oppure ormai quasi finito
            self.stato.config(text=self.t("analisi", n=n, totale=totale, pct=pct))
        else:
            self.stato.config(text=self.t("analisi_stima", n=n, totale=totale, pct=pct,
                                          tempo=formatta_durata_breve(stima)))

    def fine(self, messaggio, errore, ok=False, percorso=None, dettaglio=""):
        self.occupato = False
        self.sel_lingua.config(state="readonly")
        self.btn_aspetto.config(state="normal")
        self.btn_genera.config(state=tk.NORMAL)
        self.btn_annulla.config(state=tk.DISABLED)
        if ok and percorso:
            config = carica_config()  # qui, nel thread principale: la configurazione la scrive solo lui
            config["cartella_salvataggio"] = os.path.dirname(os.path.abspath(percorso))
            salva_config(config)
            try:  # apre il report nel browser predefinito
                aperto = webbrowser.open(Path(percorso).resolve().as_uri())
            except webbrowser.Error:
                aperto = False
            if aperto:
                self.stato.config(text=self.t("completato_aperto") + dettaglio, style="Ok.TLabel")
            else:
                self.stato.config(text=self.t("completato_salvato") + dettaglio, style="Ok.TLabel")
                messagebox.showinfo(self.t("salvato_titolo"), self.t("apertura_fallita", percorso=percorso))
            return
        self.stato.config(text=messaggio.split("\n")[0],
                          style="Errore.TLabel" if errore else "Stato.TLabel")
        if errore:
            messagebox.showerror(self.t("errore"), messaggio)
        else:
            messagebox.showinfo(self.t("info"), messaggio)


def percorso_log_errori():
    return os.path.join(os.path.dirname(percorso_config()), "errore.log")


def segnala_errore(tipo, valore, traccia):
    """Registra e mostra un errore non gestito. Senza questo, con il doppio clic la console si chiude
    all'istante e non si capisce cosa è successo."""
    testo = "".join(traceback.format_exception(tipo, valore, traccia))
    log = percorso_log_errori()
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S}  v{VERSIONE} ---\n{testo}\n")
    except OSError:
        log = "-"
    print(testo, file=sys.stderr)
    try:
        lingua = carica_config().get("lingua")
        messagebox.showerror("Media Directory Lister", traduci(lingua if lingua in LINGUE else "it", "errore_fatale",
                                                         errore=valore, log=log))
    except Exception:
        pass  # se nemmeno la finestra di errore funziona, restano la console e il file di log


def main():
    if IS_WIN:
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # testo nitido sugli schermi ad alta risoluzione
        except (AttributeError, OSError):
            pass
    segna_fase("moduli importati")
    try:
        root = tk.Tk()
        segna_fase("finestra Tk creata")
        root.report_callback_exception = segnala_errore  # errore in un pulsante: avviso + log, si continua
        App(root)
        root.after_idle(lambda: (segna_fase("finestra mostrata"), salva_log_avvio()))
        root.mainloop()
    except Exception:
        segnala_errore(*sys.exc_info())
        if sys.stdin and sys.stdin.isatty():
            input("\nPremi Invio per chiudere... / Press Enter to close...")
        sys.exit(1)


if __name__ == "__main__":
    main()
