# tracker_ui.py
from flask import Flask, request, render_template, jsonify, send_file, abort
import os, random, threading, time, json, tempfile
from utils import chunk_file, build_metadata, save_metadata, load_metadata, sha256_of_file
import socket

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
META_FOLDER = 'metadata'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(META_FOLDER, exist_ok=True)

# in-memory mapping code -> {filename, meta_path, peers: [(ip,port)], created_at}
SESSIONS = {}
SESSION_TTL = 60*60  # 1 hour expiry

def cleanup_sessions():
    while True:
        now = time.time()
        keys = list(SESSIONS.keys())
        for k in keys:
            if now - SESSIONS[k]['created_at'] > SESSION_TTL:
                # remove metadata file if exists
                mp = SESSIONS[k].get('meta_path')
                if mp and os.path.exists(mp):
                    try:
                        os.remove(mp)
                    except:
                        pass
                del SESSIONS[k]
        time.sleep(60)

threading.Thread(target=cleanup_sessions, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """
    Expect form-data:
      - file : file to share
      - peer_addr: sender's peer address e.g., 192.168.1.20:10001
      - chunk_size (optional)
    Returns JSON: {code: '123456', meta: {...}}
    """
    f = request.files.get('file')
    peer_addr = request.form.get('peer_addr')
    chunk_size = int(request.form.get('chunk_size') or (256*1024))
    if not f or not peer_addr:
        return jsonify({'error':'file and peer_addr required'}), 400

    filename = f.filename
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    f.save(save_path)

    # create chunks locally (so we can compute hashes). In real system, seeder should do it.
    chunks = chunk_file(save_path, chunk_size=chunk_size, out_dir='shared_chunks_temp')
    meta = build_metadata(save_path, chunks, chunk_size=chunk_size)
    meta_path = os.path.join(META_FOLDER, meta['filename'] + '.meta.json')
    save_metadata(meta, meta_path)

    # parse peer_addr
    try:
        ip, prt = peer_addr.split(':')
        prt = int(prt)
    except:
        return jsonify({'error':'peer_addr must be ip:port'}), 400

    code = str(random.randint(100000, 999999))
    SESSIONS[code] = {
        'filename': meta['filename'],
        'meta_path': meta_path,
        'peers': [(ip, prt)],
        'created_at': time.time()
    }

    return jsonify({'code': code, 'meta': meta})

@app.route('/api/get_info/<code>', methods=['GET'])
def api_get_info(code):
    s = SESSIONS.get(code)
    if not s:
        return jsonify({'error':'invalid code'}), 404
    return jsonify({
        'filename': s['filename'],
        'peers': s['peers']
    })

# ---- Proxy download: server pulls chunks from peer(s) and streams file to HTTP client ----
def download_chunk_from_peer(peer_ip, peer_port, filename, index, out_path, expected_hash, timeout=10):
    import socket, json
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((peer_ip, peer_port))
        req = {'cmd': 'GETCHUNK', 'filename': filename, 'index': index}
        s.send(json.dumps(req).encode('utf-8'))
        header = s.recv(65536).decode('utf-8')
        h = json.loads(header)
        if h.get('status') != 'OK':
            s.close()
            return False, f"Peer error: {h.get('msg')}"
        size = h['size']
        s.send(b'READY')
        received = 0
        with open(out_path, 'wb') as f:
            while received < size:
                chunk = s.recv(4096)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
        s.close()
        got_hash = sha256_of_file(out_path)
        if got_hash != expected_hash:
            return False, 'Hash mismatch'
        return True, 'OK'
    except Exception as e:
        return False, str(e)

@app.route('/download/<code>')
def download_proxy(code):
    s = SESSIONS.get(code)
    if not s:
        return "Invalid or expired code", 404
    meta = load_metadata(s['meta_path'])
    filename = meta['filename']
    num_chunks = meta['num_chunks']
    chunk_hashes = meta['chunk_hashes']
    tmpdir = tempfile.mkdtemp(prefix='p2p_dl_')
    parts = []
    # naive: for each chunk, try peers in list
    for i in range(num_chunks):
        got = False
        for peer in s['peers']:
            out_path = os.path.join(tmpdir, f"{filename}.chunk{i}")
            ok, msg = download_chunk_from_peer(peer[0], peer[1], filename, i, out_path, chunk_hashes[i])
            if ok:
                parts.append(out_path)
                got = True
                break
        if not got:
            return f"Failed to download chunk {i} from peers", 500
    # assemble into single file
    assembled = os.path.join(tmpdir, filename)
    with open(assembled, 'wb') as out:
        for p in parts:
            with open(p, 'rb') as f:
                out.write(f.read())
    # stream assembled file to user
    return send_file(assembled, as_attachment=True, download_name=filename)

# static files (UI)
@app.route('/static/<path:path>')
def static_files(path):
    return app.send_static_file(path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
