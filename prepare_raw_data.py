import json
import os
from yt_dlp import YoutubeDL
import subprocess


def get_clips(label_limit=1):
    """
    Lädt und filtert je einen Clip pro Datensplit (train/val/test) aus den MS-ASL JSON-Dateien.

    Aktuell:
        - Wählt nur Clips mit Labels in `range(limit)` (z.B. bei limit=1 → nur label == 0)
        - Für jeden Split wird nur das erste passende Beispiel zurückgegeben

    Args:
        limit (int): Obergrenze für zulässige Label-IDs (z.B. 100 für Klassen 0–99).

    Returns:
    tuple:
        limit (int): Obergrenze für zulässige Label-IDs (z. B. 100)
        entries (dict): Enthält pro Split ('train_entries', 'val_entries', 'test_entries') jeweils eine Liste von Clip-Dictionaries
            {
                'train_entries': [{'org_text': 'Hello', 'clean_text': 'hello', ...}],
                'val_entries': [{'org_text': 'Hello', 'clean_text': 'hello', ...}],
                'test_entries': [{'org_text': 'Hello', 'clean_text': 'hello', ...}]
            }
    """
       
    base_dir = '/Users/sami/Desktop/MS-ASL/meta/'  # Verzeichnis mit den JSON-Dateien

    # Lade und filtere Trainingseinträge (label in range(limit)), nimm das erste passende
    with open(base_dir + 'MSASL_train.json') as train_data:
        train_entries = [e for e in json.load(train_data) if e['label'] in range(label_limit)][:1]
    
    # Gleiches für Validierung
    with open(base_dir + 'MSASL_val.json') as val_data:
        val_entries = [e for e in json.load(val_data) if e['label'] in range(label_limit)][:1]

    # Gleiches für Test
    with open(base_dir + 'MSASL_test.json') as test_data:
        test_entries = [e for e in json.load(test_data) if e['label'] in range(label_limit)][:1]

    # Rückgabe als Dictionary für strukturierte Weiterverarbeitung
    return label_limit, {
        'train_entries': train_entries,
        'val_entries': val_entries,
        'test_entries': test_entries
    }

label_limit, entries = get_clips()


def create_dirs(limit, entries):
   
   """
    Erstellt die Zielordnerstruktur für Clips anhand der übergebenen Label-Grenze und Datensplits.

    Für jeden der drei Splits ('train_clips', 'val_clips', 'test_clips') wird für jedes Label 
    in range(limit) ein Unterordner erstellt.

    Die Ordnerstruktur folgt dem Muster:
        clips/<split>/<label>/
        z.B.: clips/train_clips/0/, clips/val_clips/5/, ...

    Args:
        limit (int): Obergrenze für Label-IDs (z.B. 100 für Klassen 0–99)
        entries (dict): Dictionary mit aufbereiteten Clip-Listen für 'train_entries', 'val_entries', 'test_entries'.
                        (Wird hier nicht direkt verwendet, aber zur strukturellen Konsistenz mitgegeben.)
    """
   
   for folder in ['train_clips', 'val_clips', 'test_clips']:
      for i in range(label_limit):
        path = os.path.join('clips', folder, str(i))
        os.makedirs(path, exist_ok=True)

create_dirs(label_limit, entries)



def prepare_download_information(entries):
   result={}
   for split, vals in entries.items():
      result[split] = [['Video: {}'.format(i), 
                        vals[i]['url'],  # 1
                        vals[i]['start_time'], # 2 
                        vals[i]['end_time'], # 3
                        vals[i]['fps'], # 4
                        vals[i]['url'].split("v=")[-1].split("&")[0]+'_'+vals[i]['clean_text']+'_'+'signer_id:_'+str(vals[i]['signer_id'])+'_'+str(split.split('_')[0])+'.mp4'] # 5
                        for i in range(len(vals))]
   return result

result = prepare_download_information(entries)


def download_video(url, tmp_path="temp_video.mp4"):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'outtmpl': tmp_path,
        'quiet': True,
        'merge_output_format': 'mp4'
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def cut_clip(input_path, start, end, output_path):
    command = [
        'ffmpeg',
        '-ss', str(start),
        '-to', str(end),
        '-i', input_path,
        '-c', 'copy',
        '-y',
        output_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("ffmpeg stderr:")
    print(result.stderr.decode())


def download_and_clip(url, start, end, output_dir, filename):
    temp_path = "temp_video.mp4"
    output_path = os.path.join(output_dir, filename)

    try:
        download_video(url, tmp_path=temp_path)
        cut_clip(temp_path, start, end, output_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


for split in ['train_entries', 'val_entries', 'test_entries']:
    short_split = split.split('_')[0]
    for clip in result[split]:
        _, url, start, end, _, filename = clip
        label = entries[split][0]['label']
        output_dir = os.path.join("clips", f"{short_split}_clips", str(label))

        print(f"▶Verarbeite: {filename}")

        try:
            download_and_clip(url, start, end, output_dir, filename)
        except Exception as e:
            print(f"Fehler bei {filename}: {e}")
            continue  # Nächster Clip
