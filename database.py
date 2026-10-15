# database.py
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# 資料庫連線設定 (支援 Render PostgreSQL 或本機 SQLite)
database_url = os.environ.get("DATABASE_URL", "sqlite:///sock_shop.db")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -------------------------------------------------------------
# 資料庫模型 (Models)
# -------------------------------------------------------------
class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    room_no = db.Column(db.String(20), unique=True, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, default=1)
    nightly_rate = db.Column(db.Float, nullable=False, default=280.0)
    status = db.Column(db.String(20), default='available')

    def to_dict(self):
        return {
            "id": self.id,
            "room_no": self.room_no,
            "room_type": self.room_type,
            "capacity": self.capacity,
            "nightly_rate": self.nightly_rate,
            "status": self.status
        }

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)  # 保留主關聯相容
    guest_name = db.Column(db.String(100), nullable=False)
    guest_email = db.Column(db.String(120), nullable=False)
    guest_phone = db.Column(db.String(30))
    check_in = db.Column(db.String(20), nullable=False)
    check_out = db.Column(db.String(20), nullable=False)
    nights = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid
    booking_status = db.Column(db.String(20), default='reserved') # reserved, cancelled
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 建立與明細表的關聯
    items = db.relationship('OrderItem', backref='booking', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "guest_name": self.guest_name,
            "guest_email": self.guest_email,
            "guest_phone": self.guest_phone,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "nights": self.nights,
            "total_amount": self.total_amount,
            "payment_status": self.payment_status,
            "booking_status": self.booking_status,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "items": [item.to_dict() for item in self.items]
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    room = db.relationship('Room', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "room_id": self.room_id,
            "room_no": self.room.room_no if self.room else "",
            "room_type": self.room.room_type if self.room else "",
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal
        }


# -------------------------------------------------------------
# API 路由
# -------------------------------------------------------------
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    rooms = Room.query.all()
    return jsonify([r.to_dict() for r in rooms])

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return jsonify([b.to_dict() for b in bookings])

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    data = request.get_json() or {}
    try:
        cart_items = data.get("items", [])
        # 相容舊版單一 room_id
        if not cart_items and "room_id" in data:
            cart_items = [{
                "room_id": data.get("room_id"),
                "unit_price": data.get("total_amount", 0),
                "qty": data.get("quantity", 1)
            }]

        first_room_id = cart_items[0]["room_id"] if cart_items else 1

        new_booking = Booking(
            room_id=first_room_id,
            guest_name=data.get("guest_name"),
            guest_email=data.get("guest_email"),
            guest_phone=data.get("guest_phone"),
            check_in=data.get("check_in"),
            check_out=data.get("check_out"),
            nights=data.get("nights", 1),
            total_amount=data.get("total_amount", 0),
            note=data.get("note", "")
        )
        db.session.add(new_booking)
        db.session.flush()  # 取得 new_booking.id

        # 寫入多筆訂單明細
        for item in cart_items:
            qty = int(item.get("qty", 1))
            unit_price = float(item.get("unit_price", 0))
            subtotal = qty * unit_price
            order_item = OrderItem(
                booking_id=new_booking.id,
                room_id=item.get("room_id"),
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal
            )
            db.session.add(order_item)

        db.session.commit()
        return jsonify({"message": "訂單建立成功", "booking": new_booking.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/ecpay/config', methods=['GET'])
def ecpay_config():
    return jsonify({"configured": True})

@app.route('/api/ecpay/create-order', methods=['POST'])
def ecpay_create_order():
    data = request.get_json() or {}
    booking_id = data.get("booking_id")
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"error": "找不到訂單"}), 404
    return jsonify({"redirect_url": f"/api/ecpay/mock-pay/{booking_id}"})

@app.route('/api/ecpay/mock-pay/<int:booking_id>', methods=['GET'])
def mock_pay(booking_id):
    booking = Booking.query.get(booking_id)
    if booking:
        booking.payment_status = "paid"
        db.session.commit()
    return f"<h3>訂單 #{booking_id} 付款成功！請關閉此視窗返回系統。</h3>"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)