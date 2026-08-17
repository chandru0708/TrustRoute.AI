# ⚡ TrustRoute.AI — Smart Location-Change Workflow Engine

**TrustRoute.AI** is a field-ready operational workflow engine designed to solve a critical e-commerce logistics challenge: **safely handling customer temporary address change requests while orders are out for delivery**, without introducing fraud, gate closure violations, or fleet capacity overloads.

---

## 🌟 Key Features

* **Dynamic Fraud Scoring Engine**: Rule-based scoring system evaluating behavioral risk signals (request channel, change velocity, timing window, identity history, zone jumps).
* **Multi-Constraint Dispatch Validation**: Validates slot capacity, gate closing hours, delivery promised windows, and rider workloads before approving location updates.
* **Dual Dispatcher Comparer**: Compare the **Smart Validated Workflow** against a **Baseline Naive Auto-Accept** approach side-by-side.
* **Persistent Audit Logging**: Real-time change request logs persisted to JSON (`change_requests_log.json`) across server restarts.
* **Interactive Web Dashboard**: Beautiful, responsive SPA with 4 tabs (Dashboard Overview, Request Lab Simulator, Fleet & Orders, Audit Log) with live decision visualizer stepper animations.

---

## 🛠️ Tech Stack

* **Backend**: Python 3, FastAPI, Uvicorn, Pydantic
* **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism, Dark/Light Themes), Vanilla JavaScript (ES6+)
* **Persistence**: JSON file logging (`change_requests_log.json`)

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/chandru0708/TrustRoute.AI.git
cd TrustRoute.AI

python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the Application

Start the FastAPI application with live reloading:

```bash
uvicorn main:app --reload
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 📁 Repository Structure

```
├── main.py                     # FastAPI REST server & API endpoints
├── simulation.py               # Core domain models, fraud engine & decision rules
├── requirements.txt            # Python dependencies
├── change_requests_log.json    # Persistent JSON audit log store
├── static/
│   └── index.html              # Single Page Application (SPA) dashboard UI
└── README.md                   # Project documentation
```

---

## 📜 License

MIT License. Free for educational and operational demonstration use.
