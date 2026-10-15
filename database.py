# database.py
import os
from datetime import datetime, date
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ---------------- 資料庫連線設定 ----------------
database_url = os.environ.get("DATABASE_URL", "sqlite:///sock_shop.db")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
}
db = SQLAlchemy(app)


# -------------------------------------------------------------
# 工具函式
# -------------------------------------------------------------
def _parse_date(s, default=None):
    """把字串轉成 date；支援常見格式。"""
    if s is None or s == "":
        return default
    if isinstance(s, datetime):
        return s.date()
    if isinstance(s, date):
        return s
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(s), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"invalid date: {s}")


# -------------------------------------------------------------
# Models
# -------------------------------------------------------------
class Room(db.Model):
    __tablename__ = "rooms"
    id = db.Column(db.Integer, primary_key=True)
    room_no = db.Column(db.String(20), unique=True, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, default=1)
    nightly_rate = db.Column(db.Float, nullable=False, default=280.0)
    status = db.Column(db.String(20), default="available")

    def to_dict(self):
        return {
            "id": self.id,
            "room_no": self.room_no,
            "room_type": self.room_type,
            "capacity": self.capacity,
            "nightly_rate": self.nightly_rate,
            "status": self.status,
        }


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    guest_name = db.Column(db.String(100), nullable=False)
    guest_email = db.Column(db.String(120), nullable=False)
    guest_phone = db.Column(db.String(30))
    check_in = db.Column(db.Date, nullable=False)     # ← 對應 socksql-db 的 DATE
    check_out = db.Column(db.Date, nullable=False)    # ← 對應 socksql-db 的 DATE
    nights = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    payment_status = db.Column(db.String(20), default="pending")
    booking_status = db.Column(db.String(20), default="reserved")
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship(
        "OrderItem", backref="booking", lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "guest_name": self.guest_name,
            "guest_email": self.guest_email,
            "guest_phone": self.guest_phone,
            "check_in": self.check_in.isoformat() if self.check_in else None,
            "check_out": self.check_out.isoformat() if self.check_out else None,
            "nights": self.nights,
            "total_amount": self.total_amount,
            "payment_status": self.payment_status,
            "booking_status": self.booking_status,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "items": [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    room = db.relationship("Room", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "room_no": self.room.room_no if self.room else "",
            "room_type": self.room.room_type if self.room else "",
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal,
        }


# -------------------------------------------------------------
# 啟動時建表 + 塞預設商品
# -------------------------------------------------------------
def init_db():
    with app.app_context():
        db.create_all()
        if Room.query.count() == 0:
            defaults = [
                ("R0001", "成人襪", 1, 280.0),
                ("R0002", "成人襪", 1, 280.0),
                ("R0013", "兒童襪", 1, 250.0),
                ("R0020", "兒童襪", 1, 250.0),
            ]
            for no, t, cap, price in defaults:
                db.session.add(
                    Room(room_no=no, room_type=t, capacity=cap, nightly_rate=price)
                )
            db.session.commit()


init_db()


# -------------------------------------------------------------
# API 路由
# -------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "sock-shop"})


@app.route("/api/rooms", methods=["GET"])
def get_rooms():
    rooms = Room.query.order_by(Room.room_no).all()
    return jsonify([r.to_dict() for r in rooms])


@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    limit = request.args.get("limit", 200, type=int)
    limit = max(1, min(limit or 200, 500))
    bookings = (
        Booking.query.order_by(Booking.created_at.desc()).limit(limit).all()
    )
    return jsonify([b.to_dict() for b in bookings])


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    data = request.get_json(silent=True) or {}

    # --- 必要欄位 ---
    guest_name = (data.get("guest_name") or "").strip()
    guest_email = (data.get("guest_email") or "").strip()
    if not guest_name or not guest_email:
        return jsonify({"ok": False, "error": "missing_guest_info"}), 400

    # --- items 解析（相容舊版單一 room_id）---
    cart_items = data.get("items") or []
    if not cart_items and "room_id" in data:
        cart_items = [{
            "room_id": data.get("room_id"),
            "unit_price": data.get("total_amount", 0),
            "qty": data.get("quantity", 1),
        }]
    if not cart_items:
        return jsonify({"ok": False, "error": "empty_items"}), 400

    # --- 檢查每個 room_id 都存在，並計算總金額 ---
    computed_total = 0.0
    validated_items = []
    for item in cart_items:
        try:
            room_id = int(item.get("room_id"))
            qty = int(item.get("qty", item.get("quantity", 1)))
            unit_price = float(item.get("unit_price", 0))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "invalid_item_format"}), 400

        room = db.session.get(Room, room_id)
        if not room:
            return jsonify({
                "ok": False,
                "error": f"room_id {room_id} not found",
            }), 400

        if qty < 1:
            return jsonify({"ok": False, "error": "invalid_quantity"}), 400

        if unit_price <= 0:
            unit_price = float(room.nightly_rate)

        subtotal = qty * unit_price
        computed_total += subtotal
        validated_items.append({
            "room_id": room_id,
            "qty": qty,
            "unit_price": unit_price,
            "subtotal": subtotal,
        })

    # --- 日期解析 ---
    try:
        ci = _parse_date(data.get("check_in")) or datetime.utcnow().date()
        co = _parse_date(data.get("check_out")) or ci
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    # --- 建立 Booking + OrderItem ---
    try:
        first_room_id = validated_items[0]["room_id"]

        new_booking = Booking(
            room_id=first_room_id,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=(data.get("guest_phone") or "").strip(),
            check_in=ci,
            check_out=co,
            nights=int(data.get("nights", 1) or 1),
            total_amount=computed_total,
            note=(data.get("note") or "").strip(),
        )
        db.session.add(new_booking)
        db.session.flush()  # 取得 new_booking.id

        for item in validated_items:
            db.session.add(OrderItem(
                booking_id=new_booking.id,
                room_id=item["room_id"],
                quantity=item["qty"],
                unit_price=item["unit_price"],
                subtotal=item["subtotal"],
            ))

        db.session.commit()
        return jsonify({
            "ok": True,
            "message": "訂單建立成功",
            "booking": new_booking.to_dict(),
        }), 201

    except Exception as e:
        import traceback
        app.logger.error("create_booking failed: %s", e)
        app.logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({
            "ok": False,
            "error": "server_error",
            "detail": str(e),
        }), 500


@app.route("/api/bookings/<int:bid>", methods=["GET"])
def get_booking(bid):
    b = db.session.get(Booking, bid)
    if not b:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True, "booking": b.to_dict()})


@app.route("/api/bookings/<int:bid>/status", methods=["POST"])
def update_booking_status(bid):
    data = request.get_json(silent=True) or {}
    b = db.session.get(Booking, bid)
    if not b:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if data.get("booking_status"):
        b.booking_status = data["booking_status"]
    if data.get("payment_status"):
        b.payment_status = data["payment_status"]
    db.session.commit()
    return jsonify({"ok": True, "booking": b.to_dict()})


# -------------------------------------------------------------
# 綠界 ECPay（先 mock）
# -------------------------------------------------------------
@app.route("/api/ecpay/config", methods=["GET"])
def ecpay_config():
    return jsonify({"configured": True, "mode": "mock"})


@app.route("/api/ecpay/create-order", methods=["POST"])
def ecpay_create_order():
    data = request.get_json(silent=True) or {}
    booking_id = data.get("booking_id")
    booking = db.session.get(Booking, booking_id) if booking_id else None
    if not booking:
        return jsonify({"ok": False, "error": "booking_not_found"}), 404
    return jsonify({
        "ok": True,
        "redirect_url": f"/api/ecpay/mock-pay/{booking_id}",
        "trade_no": f"MOCK{booking_id}",
    })


@app.route("/api/ecpay/mock-pay/<int:booking_id>", methods=["GET"])
def mock_pay(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking:
        booking.payment_status = "paid"
        db.session.commit()
    return (
        f"<h3>訂單 #{booking_id} 付款成功！請關閉此視窗返回系統。</h3>"
        f"<script>setTimeout(()=>window.close(),1500)</script>"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)