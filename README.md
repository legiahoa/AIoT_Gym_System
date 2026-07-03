# 🏋️‍♂️ AIoT Gym System: Real-Time Edge AI & MLOps Fitness Assistant
<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/8b2687b0-32de-4ffd-9a15-2864d57bae07" />

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Kotlin](https://img.shields.io/badge/Kotlin-Android-7F52FF?style=for-the-badge&logo=kotlin&logoColor=white)](https://kotlinlang.org/)
[![Flask](https://img.shields.io/badge/Flask-Video%20Streaming-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MQTT](https://img.shields.io/badge/MQTT-EMQX%20Broker-3C5280?style=for-the-badge&logo=eclipse&logoColor=white)](https://www.emqx.io/)
[![Firebase](https://img.shields.io/badge/Firebase-Auth%20%7C%20Firestore-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)](https://firebase.google.com/)
[![DVC](https://img.shields.io/badge/DVC-Data%20Versioning-13ADC7?style=for-the-badge&logo=dvc&logoColor=white)](https://dvc.org/)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)](https://github.com/features/actions)

> An end-to-end distributed AIoT fitness monitoring architecture utilizing an **Edge Computing** model to analyze squat posture in real-time, coupled with an automated **MLOps CI/CD pipeline** and real-time **MQTT haptic feedback** on Android devices.

---

##  Executive Summary

The **AIoT Gym System** is designed to act as a virtual personal trainer by detecting exercising posture errors (such as rounded back or insufficient depth) in real-time and providing instantaneous haptic and visual feedback to prevent injury. 

Instead of relying on bandwidth-heavy cloud video processing, this project implements a **Distributed Edge Computing architecture**:
1. **Edge Node (Python/Flask Server):** Captures webcam feeds, extracts 3D skeletal landmarks via **MediaPipe Pose**, and runs real-time inference using a lightweight **Random Forest Classifier**.
2. **IoT Communication (MQTT):** Delivers sub-50ms warning messages and control commands between the Edge Server and the mobile client via a Publish/Subscribe broker (`broker.emqx.io`).
3. **End-User Client (Android App):** Renders real-time MJPEG video streams, triggers instant haptic vibration alarms upon pose errors, and synchronizes workout session metadata to **Google Firebase Cloud Firestore**.
4. **MLOps & DataOps Pipeline:** Implements **Data Version Control (DVC)** backed by Google Drive to decouple heavy datasets/models from Git, integrated with **GitHub Actions** for automated code linting (`flake8`), model artifact retrieval, and unit testing.

---

##  System Architecture & Data Flow

The system is structured into four core interconnected pipelines:

[ Camera Feed ] ---> [ Edge Server (Python/OpenCV/MediaPipe) ]|                        |(MJPEG Stream via HTTP)    (Publish MQTT Warnings)|                        |v                        v[ User ] <---> [ Android App (Kotlin/WebView/MQTT Client) ] ---> [ Cloud Firestore ]
### 1. Overall System Architecture
* **Decoupled Processing:** Heavy computer vision tasks run locally on the Edge Processing Server, keeping CPU utilization low on mobile clients.
* **Low-Latency Communication:** Control commands (`START`/`STOP`) and warning alerts are transferred via MQTT topics (`fitness/app/command` and `fitness/iot/result`).

### 2. Edge Computer Vision Pipeline
* **Geometric Heuristic Filter:** Pre-checks user state by comparing hip and knee Y-coordinates (`y_hip vs y_knee`). The Random Forest AI model is only invoked when the user initiates a squat, reducing edge CPU consumption during standing/resting phases.
* **Repetition & Error Tracking:** A state machine dynamically updates squat stages (`up`/`down`) to count reps accurately and trigger cooldown-protected warning alarms (max 1 alert per 3 seconds to prevent spamming).

### 3. DataOps Lifecycle
* **Training Data Pipeline:** Video frames are processed into a lightweight CSV tabular dataset (`squat_dataset_extracted.csv`) containing 132 landmark features per frame ($33 \text{ landmarks} \times 4 \text{ values}: x, y, z, visibility$).
* **Session Data Pipeline:** Local video recordings are saved on the Edge Server filesystem (`static/videos`), while only lightweight session metadata (User ID, timestamp, rep count, mistake count, and video URL) is pushed to Cloud Firestore.

### 4. Automated MLOps CI Pipeline
* **Git + DVC Synergy:** Git tracks source code and `.dvc` metadata files, while heavy model artifacts (`squat_model.pkl`) and CSV datasets are versioned and stored in a Google Drive Remote bucket.
* **Continuous Integration:** Every Git push triggers a GitHub Actions workflow that sets up Python 3.11, lints code with `flake8`, authenticates and pulls the model artifact via DVC, and executes automated regression/unit tests.

---

## 🚀 Key Performance Metrics

| Metric | Measured Performance | Impact / Technical Significance |
| :--- | :--- | :--- |
| **Model Accuracy** | **99.95%** (Test Set) | Precision, Recall, and F1-Score of **1.00** across all 4 pose classes (Standing, Correct Squat, Back Error, Not Deep Enough). |
| **Edge Processing Speed** | **25 -- 30 FPS** | Smooth real-time tracking with average inference latency under **30ms** per frame. |
| **Edge CPU Utilization** | **15 -- 20%** | Lightweight tabular ML inference and geometric filtering allow deployment on resource-constrained Edge hardware (e.g., Raspberry Pi 4). |
| **MQTT Network Latency** | **< 50 ms** | Instantaneous haptic vibration feedback on Android client upon posture error detection. |
| **CI/CD Build Duration** | **1 min 27 sec** | High-speed automated verification pipeline (56s DVC artifact pull, 2s linting, 4s unit testing). |

---

##  Technology Stack

### Edge Processing Server (Python)
* **Computer Vision:** `OpenCV`, `MediaPipe Pose`
* **Machine Learning:** `scikit-learn` (Random Forest Classifier), `pandas`, `numpy`, `pickle`
* **Web & Streaming:** `Flask` (Multipart MJPEG Streaming)
* **IoT Protocol:** `paho-mqtt` (MQTT Client)

### Mobile Application (Android)
* **Language & Architecture:** `Kotlin`, Android SDK, MainActivity WebView Streamer
* **Authentication & Database:** `Google Sign-In`, `Firebase Authentication`, `Cloud Firestore` (NoSQL)
* **IoT Client:** `Eclipse Paho MQTT Client`

### MLOps & DevOps
* **CI/CD Automation:** `GitHub Actions` (`.github/workflows/ci-pipeline.yml`)
* **Data Versioning:** `DVC` (Data Version Control), Google Drive Remote Storage, Service Account Authentication
* **Code Quality & Testing:** `flake8`, Python `unittest`

---

##  Repository Structure

```text
AIoT_Gym_System/
├── .github/workflows/
│   └── ci-pipeline.yml          # GitHub Actions MLOps CI pipeline configuration
├── Android_App/                 # Kotlin Android Studio project
│   ├── app/src/main/...         # UI, Google Auth, MQTT Client, Firestore integration
│   └── build.gradle.kts
├── Python_Server/               # Edge Processing Node
│   ├── static/videos/           # Local storage for recorded workout sessions
│   ├── data_extractor.py        # Extracts 33 landmarks from raw videos to CSV
│   ├── train_model.py           # Trains Random Forest classifier & evaluates metrics
│   ├── app.py / server.py       # Flask video streaming & MQTT communication node
│   ├── requirements.txt         # Python project dependencies
│   ├── squat_model.pkl.dvc      # DVC metadata pointer for trained AI model
│   └── squat_dataset.csv.dvc    # DVC metadata pointer for tabular training data
├── .dvc/                        # DVC remote configuration
└── README.md
 Getting Started & InstallationPrerequisitesPython $\ge 3.11$Android Studio (Koala / Latest) & Android Device/Emulator connected to the same LANGit and DVC installed locally1. Edge Processing Server SetupBash# Clone the repository
git clone [https://github.com/legiahoa/AIoT_Gym_System.git](https://github.com/legiahoa/AIoT_Gym_System.git)
cd AIoT_Gym_System/Python_Server

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull heavy dataset and model artifact from DVC Remote (Requires access credentials)
dvc pull

# Start the Edge Processing Server
python app.py
The Flask server will start streaming at http://<YOUR_LOCAL_IP>:5000/video_feed and connect to the public MQTT broker (broker.emqx.io:1883).2. Android Application SetupOpen the Android_App folder in Android Studio.Add your google-services.json file from your Firebase Project into the app/ directory.In MainActivity.kt, update the Server IP address to point to your Edge Python Server's LAN IP.Build and run the APK on your Android device.🧪 Running Automated Tests & MLOps PipelineTo manually execute the unit test suite locally:Bashcd Python_Server
python -m unittest discover -v
To update model weights and trigger the GitHub Actions MLOps pipeline:Bash# After retraining with train_model.py
dvc add squat_model.pkl
dvc push
git add squat_model.pkl.dvc
git commit -m "chore(mlops): retrain squat model with updated landmark dataset"
git push origin main


** AUTHOR**
- Lê Gia Hòa
- Role: Cloud & Network Engineering Intern | Systems & MLOps 
- EnthusiastUniversity: VNU-HCM University of Information Technology (UIT)
- Email: legiahoa1515@gmail.com
- LinkedIn: linkedin.com/in/legiahoa
- GitHub: github.com/legiahoa
This project was developed as a specialized technical demonstration of integrating Computer Vision, IoT communication protocols, and modern MLOps practices into a scalable edge architecture.
