# utils.py
import os
import hashlib
import json

def chunk_file(filepath, chunk_size=1024*1024, out_dir=None):
    if out_dir is None:
        out_dir = os.path.dirname(filepath) or '.'
    os.makedirs(out_dir, exist_ok=True)

    chunks = []
    basename = os.path.basename(filepath)
    with open(filepath, 'rb') as f:
        idx = 0
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            chunk_name = f"{basename}.chunk{idx}"
            chunk_path = os.path.join(out_dir, chunk_name)
            with open(chunk_path, 'wb') as cf:
                cf.write(data)
            chunks.append(chunk_path)
            idx += 1
    return chunks

def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''):
            h.update(block)
    return h.hexdigest()

def build_metadata(original_filepath, chunk_paths, chunk_size=1024*1024):
    metadata = {
        'filename': os.path.basename(original_filepath),
        'filesize': os.path.getsize(original_filepath),
        'chunk_size': chunk_size,
        'num_chunks': len(chunk_paths),
        'chunk_hashes': []
    }
    for p in chunk_paths:
        metadata['chunk_hashes'].append(sha256_of_file(p))
    return metadata

def save_metadata(metadata, out_path):
    with open(out_path, 'w') as f:
        json.dump(metadata, f, indent=2)

def load_metadata(path):
    with open(path, 'r') as f:
        return json.load(f)
