# P2P File Sharing Tracker

A lightweight peer-to-peer (P2P) file sharing system built with Python and Flask.  
This project enables users to upload and share files across a local or remote network using a unique share code — without needing a centralized server.

---

## Features
- Peer-to-peer file sharing over LAN or WAN  
- Drag-and-drop or manual file upload support  
- Unique code generation for each file share  
- Temporary session storage with auto-expiry  
- Chunked transfer with integrity verification  
- Simple and clean Flask-based web UI  

---

## Screenshots

| Sender Interface | Receiver Interface |
|------------------|--------------------|
| ![Sender UI](screenshots/sender_view.png) | ![Receiver UI](screenshots/receiver_view.png) |

*(Add your screenshots inside the `screenshots/` folder.)*

---

## Requirements

- Python 3.8 or later  
- Flask  
- Requests  

Install dependencies:
```bash
pip install flask requests


Project Structure
P2P-File-Tracker/
│
├── tracker_ui.py         # Flask web server (Tracker)
├── peer.py               # Peer file sender/receiver
├── utils.py              # Helper functions
├── uploads/              # Uploaded files
├── metadata/             # Metadata files
├── static/
│   ├── style.css
│   └── favicon.ico
├── templates/
│   └── index.html
├── screenshots/          # Add screenshots here
└── README.md

How to Run the Project
Step 1: Clone the repository
$ git clone https://github.com/<your-username>/p2p-file-tracker.git
$ cd p2p-file-tracker

Step 2: Install dependencies
$ pip install flask requests

Step 3: Start the Tracker (Web UI)

Run the tracker in one terminal:

$ python tracker_ui.py


You’ll see:

 * Running on http://127.0.0.1:5000


Now open your browser and go to http://127.0.0.1:5000

Step 4: Start a Peer (Seeder)

Open another terminal window and run:

$ python peer.py --mode seed --file sample.txt --host 192.168.1.5 --port 7777

Step 5: Use the Web Interface

Go to the tracker web page.

Choose Sender → upload a file → get a share code.

Share the code with the receiver.

Receiver chooses Receiver → enters the code → downloads the file.

Hosting on Local Network (LAN)

Find your local IP address:

ipconfig   # (on Windows)


Use your local IP in:

tracker_ui.py (host = "0.0.0.0")

Peer command (--host <your_ip>)

Run the tracker:

$ python tracker_ui.py


Access from any device on the same network at:

http://<your_ip>:5000

Example Workflow

Sender (Seeder Terminal):

$ python peer.py --mode seed --file demo.txt --host 192.168.1.5 --port 7777


Tracker Web UI:

Upload demo.txt

Share the generated code (e.g., 432911)

Receiver (Downloader):

Enter 432911 in the receiver section.

File downloads directly from the sender peer.

Technology Stack

Python – Backend logic

Flask – Web interface

HTML / CSS / JavaScript – Frontend UI

Socket Programming – Peer communication

SHA256 – Data integrity checks

License

This project is licensed under the MIT License.
You are free to use, modify, and distribute this software with attribution.

See the LICENSE
 file for full details.

Author

Developed by Prajwal SM
GitHub: Prajwal-SM-2005