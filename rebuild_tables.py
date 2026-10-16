# rebuild_tables.py
"""
重建資料表腳本（襪子電商語意，20 筆商品）
⚠️ 會刪除舊表 rooms / bookings / order_items，資料將清空。
執行：python rebuild_tables.py
"""
from sqlalchemy import create_engine, text
from database import db, app, Product  # noqa


def rebuild():
    database_url = app.config["SQLALCHEMY_DATABASE_URI"]
    print(f"[INFO] 使用資料庫：{database_url}")

    engine = create_engine(database_url)

    with engine.begin() as conn:
        print("[INFO] 刪除舊表 rooms / bookings / order_items ...")
        conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS bookings CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS rooms CASCADE;"))

        print("[INFO] 刪除新表 orders / products（保險起見）...")
        conn.execute(text("DROP TABLE IF EXISTS order_items CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS orders CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS products CASCADE;"))

    with app.app_context():
        print("[INFO] 建立新資料表 ...")
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
            print("[INFO] 已寫入 20 筆預設商品。")

    print("[DONE] 資料表重建完成 ✅")


if __name__ == "__main__":
    rebuild()