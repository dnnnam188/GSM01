"""Seed dữ liệu mô phỏng cho GSM-01.

Chạy lại được nhiều lần: xoá sạch dữ liệu cũ rồi nạp lại (TRUNCATE ... CASCADE).
Dùng random.Random(42) nên kết quả **giống hệt nhau mỗi lần chạy** — điều kiện
cần để bộ eval ở T-008 so sánh được giữa các lần.

Điểm quan trọng: seed cố ý cài sẵn các "case khó" với `ride_code` cố định để
kịch bản demo và golden set trỏ thẳng vào được. Xem CASE_RIDES bên dưới.
"""
from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import bcrypt

from src.backend.db.connection import get_connection

RNG = random.Random(42)
NOW = datetime(2026, 8, 26, 10, 0, 0, tzinfo=UTC)
DEMO_PASSWORD = "Demo@123"

SERVICE_TYPES = ["BIKE", "GREENCAR", "LUXURY"]
SERVICE_WEIGHTS = [0.5, 0.4, 0.1]

# Bảng giá lấy từ data/knowledge_base/01_pricing_and_surcharges.md
FARE_TABLE = {
    "BIKE": {"base": 13_800, "per_km": 4_800},
    "GREENCAR": {"base": 30_500, "per_km": 15_500},
    "LUXURY": {"base": 42_000, "per_km": 21_000},
}

# business_config — đồng bộ với knowledge_base, xem ADR-006.
# Sửa con số ở đây thì PHẢI sửa file KB tương ứng, nếu không agent sẽ trả lời
# một đằng còn hệ thống xử một nẻo.
BUSINESS_CONFIG = [
    ("refund.auto_approve_max_vnd", "50000", "int",
     "Ngưỡng hoàn tiền AI được tự duyệt. Trên mức này bắt buộc HITL (KB 03 mục 2.1)"),
    ("refund.auto_approve_max_per_month", "2", "int",
     "Số lần auto-refund tối đa mỗi tài khoản mỗi tháng (KB 03 mục 4)"),
    ("refund.fraud_score_hitl_threshold", "0.5", "float",
     "Fraud score vượt ngưỡng này thì ép sang HITL dù số tiền nhỏ"),
    ("cancel.free_window_seconds", "120", "int",
     "Cửa sổ huỷ miễn phí kể từ khi tài xế nhận chuyến (KB 02 mục 1.1)"),
    ("cancel.fee_bike_vnd", "10000", "int", "Phí huỷ Xanh SM Bike (KB 02 mục 1.2)"),
    ("cancel.fee_greencar_vnd", "20000", "int", "Phí huỷ Xanh SM Taxi (KB 02 mục 1.2)"),
    ("cancel.fee_luxury_vnd", "30000", "int", "Phí huỷ Xanh SM Luxury (KB 02 mục 1.2)"),
    ("noshow.fee_bike_vnd", "15000", "int", "Phí no-show Bike (KB 02 mục 1.3)"),
    ("noshow.fee_greencar_vnd", "25000", "int", "Phí no-show Taxi (KB 02 mục 1.3)"),
    ("noshow.fee_luxury_vnd", "40000", "int", "Phí no-show Luxury (KB 02 mục 1.3)"),
    ("fare.bike_base_vnd", "13800", "int", "Giá mở cửa 2km đầu, Xanh SM Bike (KB 01)"),
    ("fare.bike_per_km_vnd", "4800", "int", "Giá mỗi km tiếp theo, Bike (KB 01)"),
    ("fare.greencar_base_vnd", "30500", "int", "Giá mở cửa 2km đầu, GreenCar HN/HCM (KB 01)"),
    ("fare.greencar_per_km_vnd", "15500", "int", "Giá mỗi km tiếp theo, GreenCar (KB 01)"),
    ("fare.luxury_base_vnd", "42000", "int", "Giá mở cửa 2km đầu, Luxury VF 8 (KB 01)"),
    ("fare.luxury_per_km_vnd", "21000", "int", "Giá mỗi km, Luxury (KB 01)"),
    ("fare.base_distance_km", "2", "int", "Số km đầu đã gồm trong giá mở cửa (KB 01)"),
    ("fare.night_start_hour", "22", "int", "Giờ bắt đầu tính phụ phí đêm (KB 01)"),
    ("fare.night_end_hour", "6", "int", "Giờ kết thúc phụ phí đêm (KB 01)"),
    ("fare.max_extra_stops", "2", "int", "Số điểm dừng thêm tối đa (KB 01)"),
    ("fare.waiting_fee_per_hour_vnd", "60000", "int", "Phí chờ quá giờ (KB 01)"),
    ("fare.extra_stop_vnd", "10000", "int", "Phí thêm mỗi điểm dừng, tối đa 2 điểm (KB 01)"),
    ("fare.night_surcharge_bike_vnd", "10000", "int", "Phụ phí đêm 22h-6h cho Bike (KB 01)"),
    ("fare.night_surcharge_car_vnd", "20000", "int", "Phụ phí đêm 22h-6h cho Taxi/Luxury (KB 01)"),
    ("route.deviation_threshold_pct", "30", "int",
     "Quãng đường thực vượt lộ trình chuẩn quá % này thì coi là đi vòng (KB 03 mục 1.2)"),
    ("complaint.claim_window_hours", "48", "int",
     "Thời hạn khiếu nại phí huỷ kể từ khi phát sinh (KB 02 mục 3)"),
    ("alert.daily_refund_cap_vnd", "2000000", "int",
     "Tổng hoàn tiền/ngày vượt mức này thì cảnh báo trên dashboard (F14)"),
    ("alert.daily_token_cap", "2000000", "int", "Tổng token/ngày vượt mức này thì cảnh báo (F14)"),
]

DISTRICTS_HN = [
    "Hoàn Kiếm", "Ba Đình", "Đống Đa", "Hai Bà Trưng", "Cầu Giấy",
    "Thanh Xuân", "Long Biên", "Tây Hồ", "Hà Đông", "Nam Từ Liêm",
]
STREETS = [
    "Nguyễn Trãi", "Trần Duy Hưng", "Láng Hạ", "Xuân Thủy", "Giải Phóng",
    "Kim Mã", "Tôn Đức Thắng", "Nguyễn Chí Thanh", "Hoàng Quốc Việt", "Lê Duẩn",
]
FIRST_NAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Vũ", "Đặng", "Bùi", "Đỗ", "Ngô"]
MID_LAST = ["Văn An", "Thị Bình", "Minh Châu", "Quốc Dũng", "Hà Giang", "Thu Hằng",
            "Khánh Linh", "Tuấn Minh", "Phương Nga", "Đức Thắng"]


def make_address() -> str:
    return f"{RNG.randint(1, 250)} {RNG.choice(STREETS)}, {RNG.choice(DISTRICTS_HN)}, Hà Nội"


def make_name() -> str:
    return f"{RNG.choice(FIRST_NAMES)} {RNG.choice(MID_LAST)}"


def make_phone() -> str:
    return f"09{RNG.randint(10_000_000, 99_999_999)}"


def compute_fare(service_type: str, distance_km: float) -> int:
    table = FARE_TABLE[service_type]
    if service_type == "LUXURY":
        fare = max(table["base"], round(distance_km * table["per_km"]))
    else:
        extra_km = max(0.0, distance_km - 2.0)
        fare = table["base"] + round(extra_km * table["per_km"])
    return int(round(fare / 500) * 500)


# ---------------------------------------------------------------------------
# Case khó cài sẵn — ride_code cố định để demo và golden set trỏ thẳng vào.
# ---------------------------------------------------------------------------
CASE_RIDES = [
    # (ride_code, kiểu case, ghi chú dùng cho kịch bản demo)
    ("XSM-DOUBLE-01", "DOUBLE_CHARGE_SMALL", "Thu trùng 32.000đ → dưới ngưỡng, AI tự duyệt"),
    ("XSM-DOUBLE-02", "DOUBLE_CHARGE_LARGE", "Thu trùng 120.000đ → trên ngưỡng, BẮT BUỘC HITL"),
    ("XSM-DETOUR-01", "ROUTE_INEFFICIENCY", "Đi vòng 8.4km/5.2km = +61% → vượt ngưỡng 30%"),
    ("XSM-DETOUR-02", "ROUTE_INEFFICIENCY", "Đi vòng 4.1km/3.6km = +14% → KHÔNG đủ điều kiện hoàn"),
    ("XSM-CANCELFEE-01", "WRONG_CANCEL_FEE", "Huỷ ở giây thứ 74 nhưng vẫn bị thu 20.000đ"),
    ("XSM-CANCELFEE-02", "CORRECT_CANCEL_FEE", "Huỷ ở phút thứ 6 → thu phí ĐÚNG, agent phải từ chối hoàn"),
    ("XSM-LOSTITEM-01", "LOST_ITEM", "Chuyến hoàn thành 3 giờ trước → còn trong hạn tìm đồ"),
    ("XSM-FAREDIFF-01", "FARE_DISCREPANCY", "Báo giá 85.000đ nhưng trừ 127.000đ"),
    ("XSM-VEHICLE-01", "SERVICE_INTERRUPTION", "Xe hết pin giữa đường, không có xe hỗ trợ"),
    ("XSM-ACTIVE-01", "ACTIVE_RIDE", "Đang IN_PROGRESS → dùng cho booking.modify"),
    ("XSM-ACTIVE-02", "ASSIGNED_RIDE", "Vừa ASSIGNED 40 giây trước → huỷ miễn phí được"),
]


def seed() -> dict[str, int]:
    counts: dict[str, int] = {}
    password_hash = bcrypt.hashpw(DEMO_PASSWORD.encode(), bcrypt.gensalt()).decode()

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "TRUNCATE csat_ratings, refund_requests, tickets, tool_calls, messages, "
            "conversations, payments, ride_events, rides, drivers, business_config, users "
            "RESTART IDENTITY CASCADE"
        )

        # --- business_config -------------------------------------------------
        cur.executemany(
            "INSERT INTO business_config (config_key, config_value, value_type, description) "
            "VALUES (%s, %s, %s, %s)",
            BUSINESS_CONFIG,
        )
        counts["business_config"] = len(BUSINESS_CONFIG)

        # --- users -----------------------------------------------------------
        users: list[tuple] = [
            ("demo.customer@gsm.vn", password_hash, "customer", "Nguyễn Minh Khang",
             "0912345678", "GOLD"),
            ("agent01@gsm.vn", password_hash, "agent", "Trần Thị Lan", "0987654321", "STANDARD"),
            ("agent02@gsm.vn", password_hash, "agent", "Lê Quốc Huy", "0987654322", "STANDARD"),
        ]
        for i in range(1, 50):
            users.append((
                f"customer{i:02d}@gsm.vn", password_hash, "customer", make_name(),
                make_phone(), RNG.choices(["STANDARD", "SILVER", "GOLD", "PLATINUM"],
                                          [0.6, 0.25, 0.1, 0.05])[0],
            ))
        cur.executemany(
            "INSERT INTO users (email, password_hash, role, full_name, phone, membership_tier) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            users,
        )
        cur.execute("SELECT id, email, role FROM users")
        rows = cur.fetchall()
        user_by_email = {r[1]: r[0] for r in rows}
        customer_ids = [r[0] for r in rows if r[2] == "customer"]
        demo_customer = user_by_email["demo.customer@gsm.vn"]
        agent01 = user_by_email["agent01@gsm.vn"]
        counts["users"] = len(users)

        # --- drivers ---------------------------------------------------------
        drivers = []
        for _i in range(20):
            svc = RNG.choices(SERVICE_TYPES, SERVICE_WEIGHTS)[0]
            drivers.append((
                make_name(), make_phone(), svc,
                f"29{RNG.choice('ABCDEFGH')}-{RNG.randint(100, 999)}.{RNG.randint(10, 99)}",
                round(RNG.uniform(4.2, 5.0), 1), RNG.randint(150, 4000),
            ))
        cur.executemany(
            "INSERT INTO drivers (full_name, phone, service_type, plate_number, rating_avg, total_trips) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            drivers,
        )
        cur.execute("SELECT id FROM drivers")
        driver_ids = [r[0] for r in cur.fetchall()]
        counts["drivers"] = len(drivers)

        # --- rides: case khó cài sẵn, tất cả gán cho demo.customer -----------
        ride_rows: list[tuple] = []
        events: list[tuple] = []
        payments: list[tuple] = []
        case_specs = {
            "XSM-DOUBLE-01": dict(svc="BIKE", status="COMPLETED", plan=4.5, actual=4.6,
                                  quoted=26_000, final=26_000, ago_h=26, double=32_000),
            "XSM-DOUBLE-02": dict(svc="GREENCAR", status="COMPLETED", plan=7.2, actual=7.4,
                                  quoted=112_000, final=120_000, ago_h=20, double=120_000),
            "XSM-DETOUR-01": dict(svc="GREENCAR", status="COMPLETED", plan=5.2, actual=8.4,
                                  quoted=80_000, final=130_000, ago_h=30, deviation=True),
            "XSM-DETOUR-02": dict(svc="BIKE", status="COMPLETED", plan=3.6, actual=4.1,
                                  quoted=23_500, final=24_000, ago_h=52, deviation=True),
            "XSM-CANCELFEE-01": dict(svc="GREENCAR", status="CANCELLED", plan=6.0, actual=None,
                                     quoted=92_000, final=None, ago_h=8,
                                     cancel_after_s=74, cancel_fee=20_000),
            "XSM-CANCELFEE-02": dict(svc="GREENCAR", status="CANCELLED", plan=5.5, actual=None,
                                     quoted=86_000, final=None, ago_h=12,
                                     cancel_after_s=372, cancel_fee=20_000),
            "XSM-LOSTITEM-01": dict(svc="GREENCAR", status="COMPLETED", plan=9.1, actual=9.3,
                                    quoted=141_000, final=141_000, ago_h=3),
            "XSM-FAREDIFF-01": dict(svc="GREENCAR", status="COMPLETED", plan=5.0, actual=5.1,
                                    quoted=85_000, final=127_000, ago_h=15),
            "XSM-VEHICLE-01": dict(svc="GREENCAR", status="COMPLETED", plan=11.0, actual=6.2,
                                   quoted=170_000, final=99_000, ago_h=40, vehicle_issue=True),
            "XSM-ACTIVE-01": dict(svc="GREENCAR", status="IN_PROGRESS", plan=6.8, actual=None,
                                  quoted=105_000, final=None, ago_h=0.2),
            "XSM-ACTIVE-02": dict(svc="BIKE", status="ASSIGNED", plan=3.2, actual=None,
                                  quoted=19_500, final=None, ago_h=0.011),
        }

        for code, _kind, _note in CASE_RIDES:
            s = case_specs[code]
            requested = NOW - timedelta(hours=s["ago_h"])
            active = s["status"] in ("COMPLETED", "IN_PROGRESS")
            started = requested + timedelta(minutes=4) if active else None
            completed = requested + timedelta(minutes=28) if s["status"] == "COMPLETED" else None
            cancelled = (requested + timedelta(seconds=s["cancel_after_s"])
                         if s["status"] == "CANCELLED" else None)
            ride_rows.append((
                code, demo_customer, RNG.choice(driver_ids), s["svc"], s["status"],
                make_address(), make_address(), s["plan"], s["actual"],
                s["quoted"], s["final"], s.get("cancel_fee", 0),
                "Khách chủ động huỷ" if cancelled else None,
                "CUSTOMER" if cancelled else None,
                "CARD", f"seed:{code}", requested, started, completed, cancelled,
            ))

        # --- rides: 300 chuyến nền -------------------------------------------
        for bg_i in range(300):
            svc = RNG.choices(SERVICE_TYPES, SERVICE_WEIGHTS)[0]
            status = RNG.choices(
                ["COMPLETED", "CANCELLED", "PENDING"], [0.78, 0.18, 0.04])[0]
            plan = round(RNG.uniform(1.5, 18.0), 1)
            actual = round(plan * RNG.uniform(0.98, 1.12), 1) if status == "COMPLETED" else None
            quoted = compute_fare(svc, plan)
            final = compute_fare(svc, actual) if actual else None
            requested = NOW - timedelta(hours=RNG.randint(2, 60 * 24))
            started = requested + timedelta(minutes=RNG.randint(2, 9)) if status == "COMPLETED" else None
            completed = (started + timedelta(minutes=RNG.randint(8, 45))) if started else None
            cancel_after = RNG.choice([45, 88, 200, 340, 520]) if status == "CANCELLED" else None
            cancelled = requested + timedelta(seconds=cancel_after) if cancel_after else None
            cancel_fee = 0
            if cancel_after and cancel_after > 120:
                cancel_fee = {"BIKE": 10_000, "GREENCAR": 20_000, "LUXURY": 30_000}[svc]
            ride_rows.append((
                f"XSM-{240000 + bg_i}", RNG.choice(customer_ids), RNG.choice(driver_ids), svc, status,
                make_address(), make_address(), plan, actual, quoted, final, cancel_fee,
                "Khách chủ động huỷ" if cancelled else None,
                "CUSTOMER" if cancelled else None,
                RNG.choices(["CASH", "CARD", "WALLET"], [0.35, 0.4, 0.25])[0],
                f"seed:bg:{bg_i}", requested, started, completed, cancelled,
            ))

        cur.executemany(
            "INSERT INTO rides (ride_code, customer_id, driver_id, service_type, status, "
            "pickup_address, dropoff_address, planned_distance_km, actual_distance_km, "
            "quoted_fare, final_fare, cancel_fee, cancel_reason, cancelled_by, payment_method, "
            "idempotency_key, requested_at, started_at, completed_at, cancelled_at) "
            "VALUES (" + ", ".join(["%s"] * 20) + ")",
            ride_rows,
        )
        counts["rides"] = len(ride_rows)

        cur.execute("SELECT id, ride_code, customer_id, final_fare, requested_at FROM rides")
        ride_index = {r[1]: r for r in cur.fetchall()}

        # --- ride_events + payments cho case khó ------------------------------
        for code, _kind, _note in CASE_RIDES:
            ride_id, _c, cust, final_fare, requested = ride_index[code]
            s = case_specs[code]
            events.append((ride_id, "REQUESTED", '{}', requested))
            events.append((ride_id, "DRIVER_ASSIGNED", '{}', requested + timedelta(seconds=30)))
            if s.get("deviation"):
                pct = round((s["actual"] / s["plan"] - 1) * 100, 1)
                events.append((
                    ride_id, "ROUTE_DEVIATION",
                    f'{{"planned_km": {s["plan"]}, "actual_km": {s["actual"]}, "deviation_pct": {pct}}}',
                    requested + timedelta(minutes=15),
                ))
            if s.get("vehicle_issue"):
                events.append((
                    ride_id, "VEHICLE_ISSUE",
                    '{"issue": "BATTERY_DEPLETED", "replacement_dispatched": false}',
                    requested + timedelta(minutes=18),
                ))
            if s["status"] == "COMPLETED":
                events.append((ride_id, "COMPLETED", '{}', requested + timedelta(minutes=28)))
                payments.append((ride_id, cust, final_fare, "CARD", "SUCCESS",
                                 f"TXN-{code}-1", requested + timedelta(minutes=29)))
                if s.get("double"):
                    payments.append((ride_id, cust, s["double"], "CARD", "SUCCESS",
                                     f"TXN-{code}-2", requested + timedelta(minutes=29, seconds=8)))
            if s["status"] == "CANCELLED":
                events.append((ride_id, "CANCELLED",
                               f'{{"cancelled_after_seconds": {s["cancel_after_s"]}}}',
                               requested + timedelta(seconds=s["cancel_after_s"])))
                payments.append((ride_id, cust, s["cancel_fee"], "CARD", "SUCCESS",
                                 f"TXN-{code}-FEE", requested + timedelta(seconds=s["cancel_after_s"] + 5)))

        cur.executemany(
            "INSERT INTO ride_events (ride_id, event_type, payload, created_at) "
            "VALUES (%s, %s, %s::jsonb, %s)", events)
        counts["ride_events"] = len(events)

        cur.executemany(
            "INSERT INTO payments (ride_id, customer_id, amount, method, status, "
            "transaction_ref, charged_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)", payments)
        counts["payments"] = len(payments)

        # --- một hội thoại + refund PENDING_HITL để dashboard có dữ liệu ------
        cur.execute(
            "INSERT INTO conversations (customer_id, thread_id, status) "
            "VALUES (%s, %s, %s) RETURNING id",
            (demo_customer, "seed-thread-hitl-001", "WAITING_HUMAN"),
        )
        conv_id = cur.fetchone()[0]
        double_ride = ride_index["XSM-DOUBLE-02"][0]
        cur.execute(
            "INSERT INTO tickets (ticket_code, customer_id, ride_id, conversation_id, category, "
            "severity, status, description, idempotency_key) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            ("TK-SEED-0001", demo_customer, double_ride, conv_id, "FARE_DISPUTE", "HIGH",
             "OPEN", "Khách báo bị trừ tiền hai lần cho cùng một chuyến đi.", "seed:ticket:1"),
        )
        ticket_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO refund_requests (refund_code, customer_id, ride_id, ticket_id, "
            "conversation_id, amount, reason_code, reason_detail, fraud_score, status, "
            "resume_thread_id, idempotency_key) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            ("RF-SEED-0001", demo_customer, double_ride, ticket_id, conv_id, 120_000,
             "DOUBLE_CHARGE", "Log thanh toán ghi nhận 2 giao dịch SUCCESS cách nhau 8 giây.",
             0.12, "PENDING_HITL", "seed-thread-hitl-001", "seed:refund:1"),
        )
        cur.execute(
            "INSERT INTO audit_log (actor_type, actor_id, action, entity_type, entity_id, reason) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            ("AI_AGENT", None, "REFUND_ESCALATED", "refund_requests", "RF-SEED-0001",
             "Số tiền 120.000đ vượt ngưỡng refund.auto_approve_max_vnd = 50.000đ"),
        )
        counts["conversations"] = 1
        counts["tickets"] = 1
        counts["refund_requests"] = 1
        counts["audit_log"] = 1
        _ = agent01  # sẽ dùng ở T-005 khi CSKH duyệt

    return counts


def main() -> None:
    counts = seed()
    print("Seed xong:")
    for key, value in counts.items():
        print(f"  {key:20s} {value:>5d}")
    print(f"\nTài khoản demo (mật khẩu chung: {DEMO_PASSWORD})")
    print("  demo.customer@gsm.vn  — khách hàng, sở hữu toàn bộ case khó")
    print("  agent01@gsm.vn        — nhân viên CSKH")
    print("\nCase khó cài sẵn:")
    for code, kind, note in CASE_RIDES:
        print(f"  {code:20s} {kind:22s} {note}")


if __name__ == "__main__":
    main()
