# auto_seeder.py
import socket
import requests
import subprocess
import json
import os
import random

TRACKER_URL = "http://127.0.0.1:5000"   # change if tracker is remote
FILE_TO_SHARE = "Demo.txt"  # change to the file you want to share


def get_local_ip():
    """Automatically find your LAN/local IP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # connect to a dummy address to get the local network interface IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def get_free_port():
    """Find a random free port"""
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def register_with_tracker(file_path, ip, port):
    """Upload file metadata to tracker"""
    peer_addr = f"{ip}:{port}"
    print(f"\n📡 Registering with tracker as peer {peer_addr}...")

    files = {'file': open(file_path, 'rb')}
    data = {'peer_addr': peer_addr}

    resp = requests.post(f"{TRACKER_URL}/api/upload", files=files, data=data)
    if resp.status_code == 200:
        info = resp.json()
        code = info.get("code")
        print(f"✅ Registration successful! Share this code: {code}")
        print("Metadata:", json.dumps(info["meta"], indent=2))
        return code
    else:
        print("❌ Tracker registration failed:", resp.text)
        return None


def start_peer(ip, port, file_path):
    """Launch the peer server in a subprocess"""
    print(f"\n🚀 Starting peer to seed file at {ip}:{port} ...")
    cmd = [
        "python",
        "peer.py",
        "--mode", "seed",
        "--file", file_path,
        "--host", ip,
        "--port", str(port)
    ]
    subprocess.Popen(cmd)
    print("✅ Peer server started successfully!")


if __name__ == "__main__":
    print("🔄 Auto Seeder Starting...")

    if not os.path.exists(FILE_TO_SHARE):
        print(f"❌ File '{FILE_TO_SHARE}' not found in this directory.")
        exit(1)

    ip = get_local_ip()
    port = get_free_port()
    code = register_with_tracker(FILE_TO_SHARE, ip, port)

    if code:
        start_peer(ip, port, FILE_TO_SHARE)
        print(f"\n🎯 Your sharing code is: {code}")
        print("Tell the receiver to use this code in the tracker UI to download the file.")
        print("\n📦 Seeder running... press CTRL+C to stop.")
    else:
        print("⚠️ Seeder aborted due to tracker registration failure.")
