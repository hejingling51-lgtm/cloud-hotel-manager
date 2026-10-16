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
# Models（襪子電商語意）
# -------------------------------------------------------------
class Product(db.Model):
    """襪子商品"""
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    product_no = db.Column(db.String(20), unique=True, nullable=False)
    product_type = db.Column(db.String(50), nullable=False)
    spec = db.Column(db.String(50), default="")
    unit_price = db.Column(db.Float, nullable=False, default=280.0)
    stock_status = db.Column(db.String(20), default="available")

    def to_dict(self):
        return {
            "id": self.id,
            "product_no": self.product_no,
            "product_type": self.product_type,
            "spec": self.spec,
            "unit_price": self.unit_price,
            "stock_status": self.stock_status,
        }


class Order(db.Model):
    """訂單"""
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(30))
    order_date = db.Column(db.Date, nullable=False)
    delivery_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    payment_status = db.Column(db.String(20), default="pending")
    order_status = db.Column(db.String(20), default="reserved")
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship(
        "OrderItem", backref="order", lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_phone": self.customer_phone,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "delivery_date": self.delivery_date.isoformat() if self.delivery_date else None,
            "total_amount": self.total_amount,
            "payment_status": self.payment_status,
            "order_status": self.order_status,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "items": [item.to_dict() for item in self.items],
        }


class OrderItem(db.Model):
    """訂單明細"""
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    product = db.relationship("Product", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_no": self.product.product_no if self.product else "",
            "product_type": self.product.product_type if self.product else "",
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal,
        }


# -------------------------------------------------------------
# 啟動時建表 + 塞 20 筆預設商品
# -------------------------------------------------------------
def init_db():
    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            for i in range(1, 21):
                product_no = f"R{i:04d}"
                if i <= 12:
                    product_type = "成人襪"
                    price = 280.0
                else:
                    product_type = "兒童襪"
                    price = 250.0
                db.session.add(
                    Product(
                        product_no=product_no,
                        product_type=product_type,
                        spec="1",
                        unit_price=price,
                    )
                )
            db.session.commit()


init_db()


# -------------------------------------------------------------
# API 路由
# -------------------------------------------------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "sock-shop"})


@app.route("/api/products", methods=["GET"])
def get_products():
    products = Product.query.order_by(Product.product_no).all()
    return jsonify([p.to_dict() for p in products])


@app.route("/api/orders", methods=["GET"])
def get_orders():
    limit = request.args.get("limit", 200, type=int)
    limit = max(1, min(limit or 200, 500))
    orders = Order.query.order_by(Order.created_at.desc()).limit(limit).all()
    return jsonify([o.to_dict() for o in orders])


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}

    customer_name = (data.get("customer_name") or "").strip()
    customer_email = (data.get("customer_email") or "").strip()
    if not customer_name or not customer_email:
        return jsonify({"ok": False, "error": "missing_customer_info"}), 400

    cart_items = data.get("items") or []
    if not cart_items and "product_id" in data:
        cart_items = [{
            "product_id": data.get("product_id"),
            "unit_price": data.get("total_amount", 0),
            "qty": data.get("quantity", 1),
        }]
    if not cart_items:
        return jsonify({"ok": False, "error": "empty_items"}), 400

    computed_total = 0.0
    validated_items = []
    for item in cart_items:
        try:
            product_id = int(item.get("product_id"))
            qty = int(item.get("qty", item.get("quantity", 1)))
            unit_price = float(item.get("unit_price", 0))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "invalid_item_format"}), 400

        product = db.session.get(Product, product_id)
        if not product:
            return jsonify({"ok": False, "error": f"product_id {product_id} not found"}), 400
        if qty < 1:
            return jsonify({"ok": False, "error": "invalid_quantity"}), 400
        if unit_price <= 0:
            unit_price = float(product.unit_price)

        subtotal = qty * unit_price
        computed_total += subtotal
        validated_items.append({
            "product_id": product_id,
            "qty": qty,
            "unit_price": unit_price,
            "subtotal": subtotal,
        })

    try:
        od = _parse_date(data.get("order_date")) or datetime.utcnow().date()
        dd = _parse_date(data.get("delivery_date")) or od
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    try:
        new_order = Order(
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=(data.get("customer_phone") or "").strip(),
            order_date=od,
            delivery_date=dd,
            total_amount=computed_total,
            note=(data.get("note") or "").strip(),
        )
        db.session.add(new_order)
        db.session.flush()

        for item in validated_items:
            db.session.add(OrderItem(
                order_id=new_order.id,
                product_id=item["product_id"],
                quantity=item["qty"],
                unit_price=item["unit_price"],
                subtotal=item["subtotal"],
            ))

        db.session.commit()
        return jsonify({
            "ok": True,
            "message": "訂單建立成功",
            "order": new_order.to_dict(),
        }), 201

    except Exception as e:
        import traceback
        app.logger.error("create_order failed: %s", e)
        app.logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({"ok": False, "error": "server_error", "detail": str(e)}), 500


@app.route("/api/orders/<int:oid>", methods=["GET"])
def get_order(oid):
    o = db.session.get(Order, oid)
    if not o:
        return jsonify({"ok": False, "error": "not_found"}), 404
    return jsonify({"ok": True, "order": o.to_dict()})


@app.route("/api/orders/<int:oid>/status", methods=["POST"])
def update_order_status(oid):
    data = request.get_json(silent=True) or {}
    o = db.session.get(Order, oid)
    if not o:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if data.get("order_status"):
        o.order_status = data["order_status"]
    if data.get("payment_status"):
        o.payment_status = data["payment_status"]
    db.session.commit()
    return jsonify({"ok": True, "order": o.to_dict()})


# -------------------------------------------------------------
# 綠界 ECPay（先 mock）
# -------------------------------------------------------------
@app.route("/api/ecpay/config", methods=["GET"])
def ecpay_config():
    return jsonify({"configured": True, "mode": "mock"})


@app.route("/api/ecpay/create-order", methods=["POST"])
def ecpay_create_order():
    data = request.get_json(silent=True) or {}
    order_id = data.get("order_id")
    order = db.session.get(Order, order_id) if order_id else None
    if not order:
        return jsonify({"ok": False, "error": "order_not_found"}), 404
    return jsonify({
        "ok": True,
        "redirect_url": f"/api/ecpay/mock-pay/{order_id}",
        "trade_no": f"MOCK{order_id}",
    })


@app.route("/api/ecpay/mock-pay/<int:order_id>", methods=["GET"])
def mock_pay(order_id):
    order = db.session.get(Order, order_id)
    if order:
        order.payment_status = "paid"
        db.session.commit()
    return (
        f"<h3>訂單 #{order_id} 付款成功！請關閉此視窗返回系統。</h3>"
        f"<script>setTimeout(()=>window.close(),1500)</script>"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)