# app.py
import os
import re
import time
import hashlib
import urllib.parse
from datetime import datetime
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from database import (
    db, Room, Booking, VisitCounter,
    seed_rooms, list_rooms, get_room, list_bookings,
    is_room_available, create_booking,
    update_booking_status, set_room_status,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==================== 绿界 ECPay 配置 ====================
ECPAY_MERCHANT_ID = os.environ.get("ECPAY_MERCHANT_ID", "").strip()
ECPAY_HASH_KEY    = os.environ.get("ECPAY_HASH_KEY", "").strip()
ECPAY_HASH_IV     = os.environ.get("ECPAY_HASH_IV", "").strip()
ECPAY_API_URL = os.environ.get(
    "ECPAY_API_URL",
    "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5",
).strip()

# 调试开关
ECPAY_DEBUG = os.environ.get("ECPAY_DEBUG", "0") == "1"


# ==================== 绿界加密工具 ====================
def ecpay_url_encode(s: str) -> str:
    """绿界专用 URL encode：
    - 只保留 -_.!*() 不编码
    - 空格转 %20
    - 十六进制转小写（绿界要求 .NET 风格）
    """
    encoded = urllib.parse.quote(s, safe="-_.!*()")
    return re.sub(r"%[0-9A-Fa-f]{2}",
                  lambda m: m.group(0).lower(), encoded)


def generate_check_mac_value(params: dict) -> str:
    """生成 CheckMacValue（SHA256）。"""
    normalized = {str(k): str(v) for k, v in params.items()
                  if k != "CheckMacValue"}
    sorted_items = sorted(normalized.items(), key=lambda x: x[0].lower())
    query_string = "&".join(f"{k}={v}" for k, v in sorted_items)
    raw = f"HashKey={ECPAY_HASH_KEY}&{query_string}&HashIV={ECPAY_HASH_IV}"
    encoded = ecpay_url_encode(raw)
    result = hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()

    if ECPAY_DEBUG:
        print("=" * 70)
        print("[ECPay DEBUG] CheckMacValue 计算过程")
        print("-" * 70)
        print("[1] 排序后的参数：")
        for k, v in sorted_items:
            print(f"    {k} = {v!r}")
        print("[2] 拼接字串 (raw)：")
        print(f"    {raw}")
        print("[3] URL encode 后：")
        print(f"    {encoded}")
        print("[4] CheckMacValue：")
        print(f"    {result}")
        print("=" * 70)

    return result


def verify_check_mac_value(params: dict) -> bool:
    """验证绿界回传的 CheckMacValue 是否正确。"""
    received = params.get("CheckMacValue", "")
    if not received:
        return False
    params_copy = {k: v for k, v in params.items() if k != "CheckMacValue"}
    expected = generate_check_mac_value(params_copy)
    if ECPAY_DEBUG and expected != received:
        print("[ECPay DEBUG] 回调验签失败")
        print(f"    received = {received}")
        print(f"    expected = {expected}")
    return expected == received


# ==================== 数据库 URI ====================
def build_db_uri():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        return url
    return f"sqlite:///{os.path.join(BASE_DIR, 'hotel.db')}"


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = build_db_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True, "pool_recycle": 280,
    }
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_rooms()
        VisitCounter.get_count()

    # ---------------- 房间 ---------------- 
    @app.route("/api/rooms", methods=["GET"])
    def api_list_rooms():
        return jsonify([r.to_dict() for r in list_rooms()])

    @app.route("/api/rooms/<int:room_id>/status", methods=["POST"])
    def api_set_room_status(room_id):
        data = request.get_json(silent=True) or {}
        status = (data.get("status") or "").strip()
        if status not in ("available", "occupied", "cleaning", "maintenance"):
            return jsonify({"ok": False, "error": "invalid_status"}), 400
        room = set_room_status(room_id, status)
        if not room:
            return jsonify({"ok": False, "error": "room_not_found"}), 404
        return jsonify({"ok": True, "room": room.to_dict()})

    # ---------------- 预订 ---------------- 
    @app.route("/api/bookings", methods=["GET"])
    def api_list_bookings():
        try:
            limit = max(1, min(int(request.args.get("limit", 200)), 500))
        except (TypeError, ValueError):
            limit = 200
        return jsonify([b.to_dict() for b in list_bookings(limit)])

    @app.route("/api/bookings", methods=["POST"])
    def api_create_booking():
        data = request.get_json(silent=True) or {}

        # --- 解析下單日 ---
        try:
            check_in = datetime.strptime(data["check_in"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            return jsonify({"ok": False, "error": "invalid_check_in"}), 400

        # --- 解析交期（若未提供，預設等於下單日）---
        try:
            check_out = datetime.strptime(
                data.get("check_out") or data["check_in"], "%Y-%m-%d"
            ).date()
        except (KeyError, ValueError):
            return jsonify({"ok": False, "error": "invalid_check_out"}), 400

        # --- 可選：前端傳來的數量與總金額 ---
        quantity = data.get("quantity")
        total_amount = data.get("total_amount")

        try:
            b = create_booking(
                room_id=int(data["room_id"]),
                guest_name=(data.get("guest_name") or "").strip(),
                guest_email=(data.get("guest_email") or "").strip(),
                guest_phone=(data.get("guest_phone") or "").strip(),
                check_in=check_in,
                check_out=check_out,
                note=(data.get("note") or "").strip(),
                quantity=int(quantity) if quantity is not None else None,
                total_override=(
                    float(total_amount)
                    if total_amount is not None else None
                ),
            )
        except ValueError as e:
            return jsonify({"ok": False, "error": str(e)}), 400
        except Exception:
            db.session.rollback()
            return jsonify({"ok": False, "error": "server_error"}), 500

        return jsonify({"ok": True, "booking": b.to_dict()}), 201

    @app.route("/api/bookings/<int:bid>/status", methods=["POST"])
    def api_update_booking_status(bid):
        data = request.get_json(silent=True) or {}
        b = update_booking_status(
            bid,
            booking_status=data.get("booking_status"),
            payment_status=data.get("payment_status"),
            stripe_session_id=data.get("stripe_session_id"),
        )
        if not b:
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "booking": b.to_dict()})

    @app.route("/api/availability", methods=["GET"])
    def api_availability():
        try:
            room_id = int(request.args["room_id"])
            ci = datetime.strptime(request.args["check_in"], "%Y-%m-%d").date()
            co = datetime.strptime(request.args["check_out"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            return jsonify({"ok": False, "error": "invalid_params"}), 400
        return jsonify({"available": is_room_available(room_id, ci, co)})

    # ---------------- 绿界 ECPay ---------------- 
    @app.route("/api/ecpay/config", methods=["GET"])
    def api_ecpay_config():
        return jsonify({
            "configured": bool(ECPAY_MERCHANT_ID and ECPAY_HASH_KEY and ECPAY_HASH_IV),
            "api_url": ECPAY_API_URL,
            "merchant_id": ECPAY_MERCHANT_ID,
        })

    def _build_ecpay_params(b: Booking):
        """
        构造绿界 AIO 参数 + CheckMacValue。
        测试阶段：
        - 移除 ClientBackURL
        - TradeDesc / ItemName 用纯字母，避免连字符和数字干扰
        """
        trade_no = f"H{int(time.time())}{b.id}"[:20]

        return_url = os.environ.get(
            "ECPAY_RETURN_URL", "https://example.com/api/ecpay/notify"
        ).strip()

        amount = int(round(float(b.total_amount)))
        if amount < 1:
            amount = 1

        params = {
            "MerchantID": ECPAY_MERCHANT_ID,
            "MerchantTradeNo": trade_no,
            "MerchantTradeDate": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "PaymentType": "aio",
            "TotalAmount": amount,
            "TradeDesc": "HotelBooking",          # ← 纯字母
            "ItemName": "RoomBooking",            # ← 纯字母
            "ReturnURL": return_url,
            "ChoosePayment": "ALL",
            "EncryptType": 1,
        }
        params["CheckMacValue"] = generate_check_mac_value(params)
        return params, trade_no

    @app.route("/api/ecpay/create-order", methods=["POST"])
    def api_ecpay_create_order():
        if not (ECPAY_MERCHANT_ID and ECPAY_HASH_KEY and ECPAY_HASH_IV):
            return jsonify({"ok": False, "error": "ecpay_not_configured"}), 500

        data = request.get_json(silent=True) or {}
        booking_id = data.get("booking_id")
        b = db.session.get(Booking, booking_id) if booking_id else None
        if not b:
            return jsonify({"ok": False, "error": "booking_not_found"}), 404

        params, trade_no = _build_ecpay_params(b)
        update_booking_status(b.id, stripe_session_id=trade_no)

        return jsonify({
            "ok": True,
            "params": params,
            "api_url": ECPAY_API_URL,
            "trade_no": trade_no,
            "redirect_url": f"/api/ecpay/redirect/{b.id}",
        })

    @app.route("/api/ecpay/redirect/<int:booking_id>", methods=["GET"])
    def api_ecpay_redirect(booking_id):
        if not (ECPAY_MERCHANT_ID and ECPAY_HASH_KEY and ECPAY_HASH_IV):
            return "ecpay_not_configured", 500

        b = db.session.get(Booking, booking_id)
        if not b:
            return "booking_not_found", 404

        params, trade_no = _build_ecpay_params(b)
        update_booking_status(b.id, stripe_session_id=trade_no)

        inputs = "".join(
            f'<input type="hidden" name="{k}" value="{v}">'
            for k, v in params.items()
        )
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>前往綠界付款 - 訂單 #{b.id}</title>
  <style>
    body {{ font-family: sans-serif; padding: 40px; text-align: center; }}
    .btn {{ display: inline-block; padding: 14px 28px;
            background: #635BFF; color: white; border: none;
            border-radius: 8px; font-size: 16px; cursor: pointer;
            text-decoration: none; font-weight: bold; }}
  </style>
</head>
<body onload="document.ecpayForm.submit();">
  <h2>正在前往綠界付款頁面…</h2>
  <p>若未自動跳轉，請點擊下方按鈕：</p>
  <form name="ecpayForm" method="post" action="{ECPAY_API_URL}">
    {inputs}
    <button type="submit" class="btn">前往綠界付款</button>
  </form>
</body>
</html>"""
        return Response(html, mimetype="text/html")

    @app.route("/api/ecpay/notify", methods=["POST"])
    def api_ecpay_notify():
        params = request.form.to_dict()
        if not verify_check_mac_value(params):
            app.logger.warning("ECPay notify CheckMacValue mismatch: %s", params)
            return "1|OK", 200, {"Content-Type": "text/plain"}

        rtn_code = params.get("RtnCode", "")
        trade_no = params.get("MerchantTradeNo", "")

        if rtn_code == "1" and trade_no:
            b = Booking.query.filter_by(stripe_session_id=trade_no).first()
            if b:
                update_booking_status(b.id, payment_status="paid")

        return "1|OK", 200, {"Content-Type": "text/plain"}

    @app.route("/api/ecpay/query/<int:booking_id>", methods=["GET"])
    def api_ecpay_query(booking_id):
        b = db.session.get(Booking, booking_id)
        if not b:
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({
            "ok": True,
            "paid": b.payment_status == "paid",
            "payment_status": b.payment_status,
            "trade_no": b.stripe_session_id or "",
        })

    # ---------------- 访问计数 ---------------- 
    @app.route("/api/visits", methods=["GET"])
    def api_get_visits():
        return jsonify({"count": VisitCounter.get_count()})

    @app.route("/api/visits", methods=["POST"])
    def api_inc_visits():
        return jsonify({"count": VisitCounter.increment()})

    @app.route("/api/health", methods=["GET"])
    def api_health():
        return jsonify({
            "ok": True,
            "payment": "ecpay",
            "ecpay_configured": bool(ECPAY_MERCHANT_ID and ECPAY_HASH_KEY and ECPAY_HASH_IV),
            "ecpay_debug": ECPAY_DEBUG,
        })

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return jsonify({"ok": False, "error": "internal_error"}), 500

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)