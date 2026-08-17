"""
FastAPI backend for the TrustRoute Temporary-Location Change Workflow.
Wraps the SmartDispatcher / BaselineDispatcher engine from simulation.py
with REST endpoints for customers and dispatchers.

Run: uvicorn main:app --reload
Then open: http://127.0.0.1:8000
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from simulation import (
    Zone, Rider, Order, ChangeRequest, OrderStatus, ChangeRequestStatus,
    BaselineDispatcher, SmartDispatcher,
)

app = FastAPI(title="TrustRoute Location-Change Workflow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory "database" -- seeded with demo zones, riders and orders so the
# frontend has something to show immediately without extra setup.
# ---------------------------------------------------------------------------

ZONES: dict[str, Zone] = {}
RIDERS: dict[str, Rider] = {}
ORDERS: dict[str, Order] = {}
CHANGE_REQUESTS: dict[str, ChangeRequest] = {}
ZONE_LOAD: dict[str, int] = {}

smart_dispatcher: Optional[SmartDispatcher] = None
baseline_dispatcher = BaselineDispatcher()


def _hour_now() -> float:
    """Represents 'now' as a 24h float clock, matching simulation.py's model.
    In this demo we use the current wall-clock hour so the UI feels live."""
    now = datetime.now()
    return now.hour + now.minute / 60.0


LOG_FILE = "change_requests_log.json"


def save_change_requests_to_file():
    data = [req_to_dict(r) for r in CHANGE_REQUESTS.values()]
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving logs to {LOG_FILE}: {e}")


def load_change_requests_from_file():
    if not os.path.exists(LOG_FILE):
        return
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            req_id = item.get("request_id")
            if not req_id or req_id in CHANGE_REQUESTS:
                continue
            order = ORDERS.get(item.get("order_id"))
            new_zone = ZONES.get(item.get("new_zone_id"))
            if not order or not new_zone:
                continue

            status_val = item.get("status", "pending")
            try:
                status_enum = ChangeRequestStatus(status_val)
            except ValueError:
                status_enum = ChangeRequestStatus.PENDING

            req = ChangeRequest(
                request_id=req_id,
                order=order,
                new_address=item.get("new_address", ""),
                new_zone=new_zone,
                requested_at=float(item.get("requested_at", 0.0)),
                channel=item.get("channel", "app"),
                status=status_enum,
                reason_log=item.get("reason_log", []),
                otp_verified=bool(item.get("otp_verified", False)),
                fraud_score=float(item.get("fraud_score", 0.0)),
            )
            CHANGE_REQUESTS[req_id] = req

            # Re-apply order location updates if the request was approved
            if status_enum in (ChangeRequestStatus.AUTO_APPROVED, ChangeRequestStatus.DISPATCHER_APPROVED):
                order.current_address = req.new_address
                order.zone = req.new_zone
                hist_item = (req.requested_at, req.new_address, req.status.value)
                if hist_item not in order.change_history:
                    order.change_history.append(hist_item)
    except Exception as e:
        print(f"Error loading logs from {LOG_FILE}: {e}")


def seed_demo_data(clear_file: bool = False):
    if clear_file and os.path.exists(LOG_FILE):
        try:
            os.remove(LOG_FILE)
        except Exception as e:
            print(f"Error removing {LOG_FILE}: {e}")

    ZONES.clear(); RIDERS.clear(); ORDERS.clear(); CHANGE_REQUESTS.clear(); ZONE_LOAD.clear()

    zone_defs = [
        ("Z1", "Palm Meadows Apartments", 8, 22.0),
        ("Z2", "Cyber Towers Office Park", 6, 20.0),
        ("Z3", "Lakeview Residency", 10, 23.0),
        ("Z4", "Tech Valley Business Hub", 5, 19.5),
        ("Z5", "Greenwood Heights", 7, 21.5),
        ("Z6", "Prestige Tech Park", 8, 22.5),
        ("Z7", "Royal Palms Villas", 4, 20.0),
        ("Z8", "Financial District Tower", 12, 23.5),
        ("Z9", "Sunrise Enclave", 6, 21.0),
        ("Z10", "Embassy GolfLinks", 9, 22.0),
    ]
    for zid, name, cap, close in zone_defs:
        ZONES[zid] = Zone(zid, name, cap, close)

    rider_defs = [
        ("R1", "Arun Kumar", 22),
        ("R2", "Priya S", 20),
        ("R3", "Mohammed Faizal", 24),
        ("R4", "Karthik Raja", 25),
        ("R5", "Ananya Roy", 20),
        ("R6", "Vikram Singh", 22),
    ]
    for rid, name, maxo in rider_defs:
        RIDERS[rid] = Rider(rid, name, maxo)

    global smart_dispatcher
    smart_dispatcher = SmartDispatcher(RIDERS, ZONES)

    now = _hour_now()
    demo_orders = [
        ("O1001", "C201", "Z1", "Palm Meadows, Block A, Flat 304", (now + 1.5, now + 3.0), "R1", 400, 20),
        ("O1002", "C202", "Z2", "Cyber Towers, Wing B, Desk 12", (now + 0.75, now + 2.0), "R2", 15, 2),
        ("O1003", "C203", "Z3", "Lakeview Residency, Tower 2, Flat 1105", (now + 2.5, now + 4.0), "R3", 90, 8),
        ("O1004", "C204", "Z4", "Tech Valley Business Hub, Tower A, Bay 4", (now + 1.0, now + 2.5), "R4", 120, 12),
        ("O1005", "C205", "Z5", "Greenwood Heights, Block C, Flat 802", (now + 0.5, now + 1.5), "R5", 300, 18),
        ("O1006", "C206", "Z6", "Prestige Tech Park, Building 3, Floor 4", (now + 2.0, now + 3.5), "R6", 5, 1),
        ("O1007", "C207", "Z7", "Royal Palms Villas, Villa 14", (now + 1.8, now + 3.2), "R1", 210, 15),
        ("O1008", "C208", "Z8", "Financial District Tower, Floor 18, Desk 5", (now + 0.8, now + 2.2), "R2", 50, 5),
        ("O1009", "C209", "Z9", "Sunrise Enclave, Sector 4, House 42", (now + 2.2, now + 3.8), "R3", 2, 0),
        ("O1010", "C210", "Z10", "Embassy GolfLinks, Block B, Suite 101", (now + 1.2, now + 2.8), "R4", 500, 30),
    ]
    for oid, cid, zid, addr, window, rid, acc_age, prior in demo_orders:
        ORDERS[oid] = Order(
            oid, cid, ZONES[zid], addr, addr, window, RIDERS[rid],
            created_at=now, account_age_days=acc_age, prior_successful_orders=prior,
        )
        RIDERS[rid].current_route.append(oid)

    if not clear_file:
        load_change_requests_from_file()


seed_demo_data()

# ---------------------------------------------------------------------------
# Pydantic request/response schemas
# ---------------------------------------------------------------------------

class ChangeRequestIn(BaseModel):
    order_id: str
    new_zone_id: str
    new_address: str
    channel: str  # "app" | "sms" | "call"
    dispatcher_type: str = "smart"  # "smart" | "baseline" -- lets the UI compare both


class DispatcherDecisionOut(BaseModel):
    request_id: str
    success: bool
    reason: str
    status: str
    fraud_score: float
    otp_verified: bool
    reason_log: list[str]


def order_to_dict(o: Order) -> dict:
    return {
        "order_id": o.order_id,
        "customer_id": o.customer_id,
        "zone_id": o.zone.zone_id,
        "zone_name": o.zone.name,
        "current_address": o.current_address,
        "original_address": o.original_address,
        "promised_window": o.promised_window,
        "rider_id": o.rider.rider_id if o.rider else None,
        "rider_name": o.rider.name if o.rider else None,
        "status": o.status.value,
        "change_history": [
            {"timestamp": round(t, 2), "address": a, "outcome": out}
            for (t, a, out) in o.change_history
        ],
    }


def zone_to_dict(z: Zone) -> dict:
    return {
        "zone_id": z.zone_id,
        "name": z.name,
        "capacity_per_slot": z.capacity_per_slot,
        "current_load": ZONE_LOAD.get(z.zone_id, 0),
        "gate_close_time": z.gate_close_time,
    }


def req_to_dict(r: ChangeRequest) -> dict:
    return {
        "request_id": r.request_id,
        "order_id": r.order.order_id,
        "new_zone_id": r.new_zone.zone_id,
        "new_address": r.new_address,
        "channel": r.channel,
        "requested_at": round(r.requested_at, 2),
        "status": r.status.value,
        "fraud_score": round(r.fraud_score, 3),
        "otp_verified": r.otp_verified,
        "reason_log": r.reason_log,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/orders")
def list_orders():
    return [order_to_dict(o) for o in ORDERS.values()]


@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    order = ORDERS.get(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order_to_dict(order)


@app.get("/api/zones")
def list_zones():
    return [zone_to_dict(z) for z in ZONES.values()]


@app.get("/api/riders")
def list_riders():
    return [
        {
            "rider_id": r.rider_id, "name": r.name,
            "max_daily_orders": r.max_daily_orders,
            "current_load": len(r.current_route),
        }
        for r in RIDERS.values()
    ]


@app.get("/api/change-requests")
def list_change_requests():
    return [req_to_dict(r) for r in CHANGE_REQUESTS.values()]


@app.post("/api/change-request", response_model=DispatcherDecisionOut)
def submit_change_request(payload: ChangeRequestIn):
    order = ORDERS.get(payload.order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    new_zone = ZONES.get(payload.new_zone_id)
    if not new_zone:
        raise HTTPException(404, "Destination zone not found")

    now = _hour_now()
    request_id = str(uuid.uuid4())[:8]
    req = ChangeRequest(request_id, order, payload.new_address, new_zone, now, payload.channel)
    CHANGE_REQUESTS[request_id] = req

    if payload.dispatcher_type == "baseline":
        success, reason = baseline_dispatcher.handle_change_request(req, now, ZONE_LOAD)
    else:
        success, reason = smart_dispatcher.handle_change_request(req, now, ZONE_LOAD)

    save_change_requests_to_file()

    return DispatcherDecisionOut(
        request_id=req.request_id,
        success=success,
        reason=reason,
        status=req.status.value,
        fraud_score=round(req.fraud_score, 3),
        otp_verified=req.otp_verified,
        reason_log=req.reason_log,
    )


@app.get("/api/dashboard/summary")
def dashboard_summary():
    total = len(CHANGE_REQUESTS)
    approved = sum(1 for r in CHANGE_REQUESTS.values()
                    if r.status.value in ("auto_approved", "dispatcher_approved"))
    rejected = sum(1 for r in CHANGE_REQUESTS.values() if r.status.value == "rejected")
    fraud_flagged = sum(1 for r in CHANGE_REQUESTS.values() if r.status.value == "flagged_fraud")
    avg_fraud_score = (
        round(sum(r.fraud_score for r in CHANGE_REQUESTS.values()) / total, 3) if total else 0
    )
    return {
        "total_requests": total,
        "approved": approved,
        "rejected": rejected,
        "fraud_flagged": fraud_flagged,
        "average_fraud_score": avg_fraud_score,
        "zones": [zone_to_dict(z) for z in ZONES.values()],
    }


@app.post("/api/reset-demo")
def reset_demo():
    seed_demo_data(clear_file=True)
    return {"status": "reset", "message": "Demo data reseeded and logs cleared"}


# ---------------------------------------------------------------------------
# Serve the frontend
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_index():
    return FileResponse("static/index.html")
