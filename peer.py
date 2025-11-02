# peer.py
import socket, threading, json, os, argparse
from utils import chunk_file, build_metadata, save_metadata, load_metadata, sha256_of_file

CHUNK_DIR = 'shared_chunks'
DOWNLOAD_DIR = 'downloads'
METADATA_DIR = 'metadata'

def handle_peer_conn(conn, addr, peer_chunk_dir):
    try:
        data = conn.recv(16384).decode('utf-8')
        if not data:
            return
        msg = json.loads(data)
        cmd = msg.get('cmd')
        if cmd == 'GETCHUNK':
            filename = msg['filename']
            idx = msg['index']
            chunk_name = f"{filename}.chunk{idx}"
            chunk_path = os.path.join(peer_chunk_dir, chunk_name)
            if not os.path.exists(chunk_path):
                conn.send(json.dumps({'status': 'ERR', 'msg': 'No chunk'}).encode('utf-8'))
                return
            size = os.path.getsize(chunk_path)
            header = {'status': 'OK', 'size': size}
            conn.send(json.dumps(header).encode('utf-8'))
            ack = conn.recv(16)
            with open(chunk_path, 'rb') as f:
                while True:
                    b = f.read(4096)
                    if not b:
                        break
                    conn.sendall(b)
        else:
            conn.send(json.dumps({'status': 'ERR', 'msg': 'Unknown command'}).encode('utf-8'))
    except Exception as e:
        print('Peer server error', e)
    finally:
        conn.close()

def start_peer_server(listen_host, listen_port, peer_chunk_dir):
    os.makedirs(peer_chunk_dir, exist_ok=True)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((listen_host, listen_port))
    s.listen(10)
    print(f"[Peer] Serving chunks from {peer_chunk_dir} on {listen_host}:{listen_port}")
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_peer_conn, args=(conn, addr, peer_chunk_dir), daemon=True).start()
    except KeyboardInterrupt:
        print("[Peer] Server shutdown")
    finally:
        s.close()

def download_chunk_from_peer(peer_ip, peer_port, filename, index, out_path, expected_hash):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
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

def download_file_direct(filename, meta_path, target_dir, peers_info):
    meta = load_metadata(meta_path)
    num_chunks = meta['num_chunks']
    chunk_hashes = meta['chunk_hashes']
    os.makedirs(target_dir, exist_ok=True)
    temp_dir = os.path.join(target_dir, f"{filename}.parts")
    os.makedirs(temp_dir, exist_ok=True)

    # chunk -> list of peers
    chunk_to_peers = {i: [] for i in range(num_chunks)}
    for p in peers_info:
        peer = tuple(p)  # (ip,port)
        for i in range(num_chunks):
            chunk_to_peers[i].append(peer)

    results = [None]*num_chunks
    def worker(i):
        peers_for_chunk = chunk_to_peers.get(i, [])
        expected_hash = chunk_hashes[i]
        out_path = os.path.join(temp_dir, f"{filename}.chunk{i}")
        for peer in peers_for_chunk:
            ok, msg = download_chunk_from_peer(peer[0], peer[1], filename, i, out_path, expected_hash)
            if ok:
                results[i] = (True, out_path)
                return
        results[i] = (False, f'All peers failed for chunk {i}')

    threads = []
    for i in range(num_chunks):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

    for i, r in enumerate(results):
        if not r or not r[0]:
            print(f"Failed chunk {i} -> {r}")
            return False
    assembled_path = os.path.join(target_dir, filename)
    with open(assembled_path, 'wb') as out:
        for i in range(num_chunks):
            part_path = results[i][1]
            with open(part_path, 'rb') as pf:
                out.write(pf.read())
    print(f"Assembled file at {assembled_path}")
    return True

def seed_file(filepath, chunk_size=1024*256, out_dir=CHUNK_DIR):
    os.makedirs(out_dir, exist_ok=True)
    chunks = chunk_file(filepath, chunk_size=chunk_size, out_dir=out_dir)
    meta = build_metadata(filepath, chunks, chunk_size=chunk_size)
    os.makedirs(METADATA_DIR, exist_ok=True)
    meta_path = os.path.join(METADATA_DIR, meta['filename'] + '.meta.json')
    save_metadata(meta, meta_path)
    print("[Seed] Created metadata at", meta_path)
    return meta_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['server','seed','download_direct'], required=True)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=10001)
    parser.add_argument('--file', help='file to seed')
    parser.add_argument('--meta', help='path to metadata for download_direct')
    parser.add_argument('--peer', help='peer list for download_direct as ip:port,ip2:port2')
    args = parser.parse_args()

    if args.mode == 'server':
        start_peer_server(args.host, args.port, CHUNK_DIR)

    elif args.mode == 'seed':
        if not args.file:
            print("Provide --file to seed")
        else:
            meta = seed_file(args.file)
            print("Now run server (same machine) to start serving chunks.")
            start_peer_server(args.host, args.port, CHUNK_DIR)

    elif args.mode == 'download_direct':
        if not args.meta or not args.peer:
            print("Provide --meta and --peer")
        else:
            peers = []
            for p in args.peer.split(','):
                ip, prt = p.split(':')
                peers.append((ip, int(prt)))
            filename = os.path.basename(args.meta).replace('.meta.json','')
            download_file_direct(filename, args.meta, DOWNLOAD_DIR, peers)
