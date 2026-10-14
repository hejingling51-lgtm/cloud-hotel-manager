# database.py
from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import update, and_, or_

db = SQLAlchemy()


class Room(db.Model):
    __tablename__ = "rooms"
    id = db.Column(db.Integer, primary_key=True)
    room_no = db.Column(db.String(10), unique=True, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)
    nightly_rate = db.Column(db.Numeric(10, 2), nullable=False)
    capacity = db.Column(db.Integer, default=2)
    status = db.Column(db.String(20), default="available")
    # available / occupied / cleaning / maintenance

    def to_dict(self):
        return {
            "id": self.id, "room_no": self.room_no,
            "room_type": self.room_type,
            "nightly_rate": float(self.nightly_rate),
            "capacity": self.capacity, "status": self.status,
        }


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    guest_name = db.Column(db.String(100), nullable=False)
    guest_email = db.Column(db.String(160), nullable=False)
    guest_phone = db.Column(db.String(30))
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    nights = db.Column(db.Integer, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.String(20), default="pending")
    # pending / paid / refunded / cancelled
    stripe_session_id = db.Column(db.String(200))
    booking_status = db.Column(db.String(20), default="reserved")
    # reserved / checked_in / checked_out / cancelled
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "room_id": self.room_id,
            "guest_name": self.guest_name,
            "guest_email": self.guest_email,
            "guest_phone": self.guest_phone or "",
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat(),
            "nights": self.nights,
            "total_amount": float(self.total_amount),
            "payment_status": self.payment_status,
            "booking_status": self.booking_status,
            "stripe_session_id": self.stripe_session_id or "",
            "note": self.note or "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M"),
        }


class VisitCounter(db.Model):
    __tablename__ = "visit_counter"
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, nullable=False, default=0)

    @staticmethod
    def get_count():
        row = db.session.get(VisitCounter, 1)
        if row is None:
            row = VisitCounter(id=1, count=0)
            db.session.add(row)
            db.session.commit()
        return row.count

    @staticmethod
    def increment():
        row = db.session.get(VisitCounter, 1)
        if row is None:
            row = VisitCounter(id=1, count=0)
            db.session.add(row)
            db.session.commit()
        db.session.execute(
            update(VisitCounter).where(VisitCounter.id == 1)
            .values(count=VisitCounter.count + 1)
        )
        db.session.commit()
        db.session.expire_all()
        return db.session.get(VisitCounter, 1).count


# ---------- 業務函式 ----------
def seed_rooms():
    """若房間表為空，自動建立 24 間套房。"""
    if Room.query.count() > 0:
        return
    for i in range(1, 25):
        if i <= 12:
            rtype, rate, cap = "成人襪", 280.00, 2
        elif i <= 20:
            rtype, rate, cap = "兒童襪", 480.00, 3
        else:
            rtype, rate, cap = "其它", 780.00, 4
        db.session.add(Room(
            room_no=f"R{i:03d}", room_type=rtype,
            nightly_rate=rate, capacity=cap, status="available",
        ))
    db.session.commit()


def list_rooms():
    return Room.query.order_by(Room.room_no).all()


def get_room(room_id):
    return db.session.get(Room, room_id)


def list_bookings(limit=200):
    return (Booking.query.order_by(Booking.created_at.desc())
            .limit(limit).all())


def is_room_available(room_id, check_in, check_out, exclude_booking_id=None):
    """检查某房在日期区间内是否可用。"""
    q = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.booking_status.in_(["reserved", "checked_in"]),
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    )
    if exclude_booking_id:
        q = q.filter(Booking.id != exclude_booking_id)
    return q.first() is None


def create_booking(room_id, guest_name, guest_email, guest_phone,
                   check_in, check_out, note="",
                   quantity=None, total_override=None):
    """
    建立訂單。

    參數：
      room_id        產品 / 房間 ID
      guest_name     聯絡人姓名
      guest_email    聯絡人 Email
      guest_phone    聯絡人電話
      check_in       下單日
      check_out      交期（允許等於 check_in）
      note           備註
      quantity       數量（若提供，以此為準；否則以日期差計算）
      total_override 自訂總金額（可選）。基於安全考量，
                     不得低於「單價 × 數量」的 50%，否則忽略。

    例外：
      ValueError("room_not_found")    找不到產品
      ValueError("invalid_dates")     交期早於下單日
      ValueError("room_not_available") 該區間已有訂單佔用
    """
    room = get_room(room_id)
    if not room:
        raise ValueError("room_not_found")

    # 允許同日下單（check_out == check_in）
    if check_out < check_in:
        raise ValueError("invalid_dates")

    # 決定數量
    if quantity is None:
        quantity = max(1, (check_out - check_in).days)
    else:
        try:
            quantity = max(1, int(quantity))
        except (TypeError, ValueError):
            quantity = 1

    # 檢查該區間是否已被佔用
    if not is_room_available(room_id, check_in, check_out):
        raise ValueError("room_not_available")

    # 以資料庫單價為基準計算金額
    base_total = float(room.nightly_rate) * quantity

    total = base_total
    if total_override is not None:
        try:
            override = float(total_override)
        except (TypeError, ValueError):
            override = 0
        # 安全檢查：不得低於原價 50%
        if override > 0 and override >= base_total * 0.5:
            total = override

    b = Booking(
        room_id=room_id,
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
        check_in=check_in,
        check_out=check_out,
        nights=quantity,
        total_amount=total,
        note=note,
    )
    db.session.add(b)
    db.session.commit()
    return b


def update_booking_status(booking_id, booking_status=None,
                          payment_status=None, stripe_session_id=None):
    b = db.session.get(Booking, booking_id)
    if not b:
        return None
    if booking_status:
        b.booking_status = booking_status
        # 同步更新房间状态
        room = get_room(b.room_id)
        if room:
            if booking_status == "checked_in":
                room.status = "occupied"
            elif booking_status == "checked_out":
                room.status = "cleaning"
            elif booking_status == "cancelled":
                room.status = "available"
    if payment_status:
        b.payment_status = payment_status
    if stripe_session_id:
        b.stripe_session_id = stripe_session_id
    db.session.commit()
    return b


def set_room_status(room_id, status):
    room = get_room(room_id)
    if room:
        room.status = status
        db.session.commit()
    return room