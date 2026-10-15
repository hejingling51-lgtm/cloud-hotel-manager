# hotel_app.py
import os
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:5000")

st.set_page_config(
    page_title="Gabriel-JL 雲端",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
#  CSS
# ============================================================
st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.main .block-container {padding-top: 4rem; max-width: 1200px;}

.hero {
    position: relative;
    background: linear-gradient(180deg, #e0f7fa 0%, #b2ebf2 40%, #4fc3f7 70%, #0288d1 100%);
    background-size: 100% 200%;
    animation: oceanFlow 8s ease-in-out infinite;
    color: #01579b;
    padding: 13px 40px 27px;
    border-radius: 0;
    border: none;
    text-align: center;
    margin-bottom: 24px;
    overflow: hidden;
    box-shadow: none;
    min-height: 53px;
}

@keyframes oceanFlow {
    0%   { background-position: 0% 0%; }
    50%  { background-position: 0% 100%; }
    100% { background-position: 0% 0%; }
}

.hero::before {
    content: "";
    position: absolute;
    left: 0; right: 0; bottom: 0;
    height: 60%;
    background: radial-gradient(ellipse at 20% 100%, rgba(255,255,255,0.35) 0%, transparent 60%),
                radial-gradient(ellipse at 70% 100%, rgba(255,255,255,0.25) 0%, transparent 60%);
    animation: waveShift 6s ease-in-out infinite alternate;
    pointer-events: none;
}
@keyframes waveShift {
    0%   { transform: translateX(-20px); }
    100% { transform: translateX(20px); }
}

.hero .ducks {
    position: absolute;
    right: 20px;
    bottom: 10px;
    left: auto;
    display: flex;
    justify-content: flex-end;
    align-items: flex-end;
    gap: 12px;
    pointer-events: none;
    z-index: 2;
}
.hero .ducks span {
    display: inline-block;
    line-height: 1;
    animation: duckFloat 2.5s ease-in-out infinite;
}
.hero .ducks span:nth-child(1) { font-size: 1.1rem;  animation-delay: 0s;   }
.hero .ducks span:nth-child(2) { font-size: 0.85rem; animation-delay: 0.4s; }
.hero .ducks span:nth-child(3) { font-size: 0.6rem;  animation-delay: 0.8s; }

@keyframes duckFloat {
    0%, 100% { transform: translateY(0) rotate(-4deg); }
    50%      { transform: translateY(-6px) rotate(4deg); }
}

.prod-card {
    border: 1px solid #eee; border-radius: 16px;
    padding: 16px; text-align: center; background: #fff;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06); height: 100%;
}
.prod-card h4 {margin: 0 0 6px; color: #1a1a2e; font-size: 1.2rem;}
.prod-card .spec {color: #888; font-size: 0.9rem;}
.prod-card .price {color: #e94560; font-weight: 800; font-size: 1.35rem; margin-top: 10px;}
.prod-card .price span {font-size: 0.85rem; color: #999; font-weight: 500;}

.section-title {
    font-size: 1.5rem; font-weight: 700; color: #1a1a2e;
    margin: 24px 0 12px; padding-left: 12px;
    border-left: 5px solid #e94560;
}
.footer {
    margin-top: 60px; padding: 30px; text-align: center;
    color: #999; font-size: 0.85rem; border-top: 1px solid #eee;
}
.total-box {
    background:#fff5f7; border:2px solid #e94560;
    border-radius:12px; padding:20px; text-align:center; margin-top:16px;
}
.total-box .label {color:#888; font-size:0.95rem;}
.total-box .amount {color:#e94560; font-size:2.2rem; font-weight:800;}
</style>
""", unsafe_allow_html=True)


# ============================================================
#  API 與資料處理輔助
# ============================================================
def _get(path, default=None, timeout=8):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=timeout)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return default


def _post(path, payload=None, timeout=8):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload or {}, timeout=timeout)
        return r.ok, (r.json() if r.content else {})
    except Exception as e:
        return False, {"error": str(e)}


def process_rooms(rooms):
    if not isinstance(rooms, list) or len(rooms) == 0:
        rooms = [
            {"id": 1, "room_no": "R0001", "room_type": "成人襪", "capacity": 1, "nightly_rate": 280, "status": "available"},
            {"id": 2, "room_no": "R0002", "room_type": "成人襪", "capacity": 1, "nightly_rate": 280, "status": "available"},
            {"id": 3, "room_no": "R0003", "room_type": "成人襪", "capacity": 1, "nightly_rate": 280, "status": "available"},
            {"id": 4, "room_no": "R0004", "room_type": "成人襪", "capacity": 1, "nightly_rate": 280, "status": "available"},
            {"id": 5, "room_no": "R0005", "room_type": "成人襪", "capacity": 1, "nightly_rate": 280, "status": "available"},
            {"id": 13, "room_no": "R0013", "room_type": "兒童襪", "capacity": 1, "nightly_rate": 250, "status": "available"},
            {"id": 14, "room_no": "R0014", "room_type": "兒童襪", "capacity": 1, "nightly_rate": 250, "status": "available"},
            {"id": 15, "room_no": "R0015", "room_type": "兒童襪", "capacity": 1, "nightly_rate": 250, "status": "available"},
            {"id": 16, "room_no": "R0016", "room_type": "兒童襪", "capacity": 1, "nightly_rate": 250, "status": "available"},
            {"id": 17, "room_no": "R0017", "room_type": "兒童襪", "capacity": 1, "nightly_rate": 250, "status": "available"},
        ]
        
    processed = []
    for r in rooms:
        if not isinstance(r, dict):
            continue
        r_copy = r.copy()
        try:
            room_no_str = str(r_copy.get("room_no", "R0001"))
            digits = ''.join(filter(str.isdigit, room_no_str))
            num = int(digits) if digits else 1
            r_copy["room_no"] = f"R{num:04d}"
            
            if 13 <= num <= 17:
                r_copy["room_type"] = "兒童襪"
            elif 1 <= num <= 5:
                r_copy["room_type"] = "成人襪"
            else:
                r_copy["room_type"] = r_copy.get("room_type", "成人襪")
                
            r_copy["nightly_rate"] = float(r_copy.get("nightly_rate", 280) or 280)
            r_copy["capacity"] = int(r_copy.get("capacity", 1) or 1)
            r_copy["status"] = r_copy.get("status", "available")
            r_copy["id"] = r_copy.get("id", num)
        except Exception:
            r_copy["nightly_rate"] = 280.0
            r_copy["capacity"] = 1
            r_copy["room_type"] = "成人襪"
            r_copy["status"] = "available"
        processed.append(r_copy)
    return processed


def api_get_rooms():
    try:
        r = requests.get(f"{API_BASE}/api/rooms", timeout=3)
        if r.ok:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return process_rooms(data)
    except Exception:
        pass
    return process_rooms([])


def api_create_booking(payload):
    try:
        r = requests.post(f"{API_BASE}/api/bookings", json=payload, timeout=8)
        return r.status_code == 201, r.json()
    except Exception as e:
        return False, {"error": str(e)}


def api_ecpay_config():
    return _get("/api/ecpay/config", {"configured": False}, timeout=5)


def api_ecpay_create_order(booking_id):
    return _post("/api/ecpay/create-order", {"booking_id": booking_id}, timeout=10)


def get_product_image(room_no, room_type="成人襪"):
    try:
        clean_no = str(room_no).upper().strip()
        if not clean_no.startswith("R"):
            clean_no = f"R{clean_no}"
            
        folder_name = "成人襪" if "成人" in str(room_type) else "兒童襪"
        
        img_path = os.path.join("images", folder_name, f"{clean_no}.jpg")
        if os.path.exists(img_path):
            return img_path
            
        fallback_path = os.path.join("images", f"{clean_no}.jpg")
        if os.path.exists(fallback_path):
            return fallback_path
    except Exception:
        pass
    return None


# ============================================================
#  導航與狀態
# ============================================================
if "page" not in st.session_state:
    st.session_state.page = "🏠 首頁"
if "cart" not in st.session_state:
    st.session_state.cart = []

cols = st.columns([1.5, 1, 1, 1, 1, 1, 1, 1])
with cols[0]:
    st.markdown("<div style='font-weight:700;font-size:1.1rem;color:#1a1a2e;padding-top:6px;'>🏢 Gabriel-JL 雲端</div>", unsafe_allow_html=True)

nav_items = [
    ("🏠 首頁", cols[1]), ("🛍️ 產品介紹", cols[2]),
    ("📝 組合詢價", cols[3]), ("🛒 購物車", cols[4]),
    ("🛒 線上下單", cols[5]), ("📷 相片瀏覽", cols[6]),
]
for label, col in nav_items:
    with col:
        if st.button(label, use_container_width=True, key=f"nav_{label}"):
            st.session_state.page = label
            st.rerun()

with cols[7]:
    if st.button("🔐 管理", use_container_width=True, key="nav_admin"):
        st.session_state.show_admin = not st.session_state.get("show_admin", False)
        st.rerun()

page = st.session_state.page

# ---------- 首頁 ----------
if page == "🏠 首頁":
    st.markdown("<div class='hero'><div class='ducks'><span>🦆</span><span>🦆</span><span>🦆</span></div></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">熱門產品</div>', unsafe_allow_html=True)
    rooms = api_get_rooms()
    if rooms:
        for i in range(0, min(len(rooms), 10), 4):
            cols4 = st.columns(4)
            for j, r in enumerate(rooms[i:i+4]):
                with cols4[j]:
                    img_path = get_product_image(r['room_no'], r['room_type'])
                    if img_path:
                        st.image(img_path, use_column_width=True)
                    else:
                        st.info("📷 暫無圖片")
                    st.markdown(
                        f"<div class='prod-card' style='border-top:none; border-top-left-radius:0; border-top-right-radius:0;'>"
                        f"<h4>{r['room_no']}</h4>"
                        f"<p class='spec'>{r['room_type']} · 規格 {r['capacity']}</p>"
                        f"<p class='price'>NT${r['nightly_rate']:.0f}<span>/ 單位</span></p>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

# ---------- 產品介紹 ----------
elif page == "🛍️ 產品介紹":
    st.markdown('<div class="section-title">產品介紹</div>', unsafe_allow_html=True)
    rooms = api_get_rooms()
    if rooms:
        types = {}
        for r in rooms:
            types.setdefault(r["room_type"], []).append(r)
        for ptype, items in types.items():
            st.markdown(f"#### {ptype}")
            for i in range(0, len(items), 3):
                cols3 = st.columns(3)
                for j, p in enumerate(items[i:i + 3]):
                    with cols3[j]:
                        img_path = get_product_image(p['room_no'], p['room_type'])
                        if img_path:
                            st.image(img_path, use_column_width=True)
                        else:
                            st.info("📷 暫無圖片")
                        st.markdown(
                            f"<div class='prod-card' style='border-top:none; border-top-left-radius:0; border-top-right-radius:0;'>"
                            f"<h4>{p['room_no']}</h4>"
                            f"<p class='spec'>{p['room_type']} · 規格 {p['capacity']}</p>"
                            f"<p class='price'>NT${p['nightly_rate']:.0f}<span>/ 單位</span></p>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

# ---------- 組合詢價 ----------
elif page == "📝 組合詢價":
    st.markdown('<div class="section-title">組合詢價</div>', unsafe_allow_html=True)
    st.caption("點選 − / + 調整數量，系統即時試算總價。價格滿意即可加入購物車。")
    rooms = api_get_rooms()
    if rooms:
        for r in rooms:
            key = f"qty_{r['id']}"
            if key not in st.session_state:
                st.session_state[key] = 0

        st.markdown("### 🛍️ 選擇產品與數量")
        for r in rooms:
            key = f"qty_{r['id']}"
            qty = st.session_state[key]
            subtotal = r["nightly_rate"] * qty
            c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 2])
            with c1:
                st.write(f"**{r['room_no']} {r['room_type']}** (NT${r['nightly_rate']:.0f}/單位)")
            with c2:
                if st.button("−", key=f"minus_{r['id']}", use_container_width=True):
                    if st.session_state[key] > 0:
                        st.session_state[key] -= 1
                    st.rerun()
            with c3:
                st.write(f"**{qty}**")
            with c4:
                if st.button("+", key=f"plus_{r['id']}", use_container_width=True):
                    st.session_state[key] += 1
                    st.rerun()
            with c5:
                st.write(f"NT${subtotal:,.0f}" if qty > 0 else "—")

        selected = [(r, st.session_state[f"qty_{r['id']}"]) for r in rooms if st.session_state[f"qty_{r['id']}"] > 0]
        if selected:
            st.markdown("### 🧾 組合試算")
            total = sum(r["nightly_rate"] * qty for r, qty in selected)
            for r, qty in selected:
                st.write(f"- {r['room_no']} {r['room_type']} × {qty} = NT${r['nightly_rate'] * qty:,.0f}")
            st.markdown(f"**總計：NT${total:,.0f}**")
            if st.button("✅ 加入購物車", type="primary"):
                for r, qty in selected:
                    st.session_state.cart.append({"room_id": r["id"], "name": f"{r['room_no']} {r['room_type']}", "unit_price": r["nightly_rate"], "qty": qty})
                    st.session_state[f"qty_{r['id']}"] = 0
                st.success("已加入購物車！")
                st.rerun()

# ---------- 購物車 ----------
elif page == "🛒 購物車":
    st.markdown('<div class="section-title">購物車</div>', unsafe_allow_html=True)
    cart = st.session_state.cart
    if not cart:
        st.info("購物車是空的，請至「📝 組合詢價」選擇產品。")
    else:
        total = 0
        for i, item in enumerate(cart):
            subtotal = item["unit_price"] * item["qty"]
            total += subtotal
            st.write(f"- **{item['name']}** × {item['qty']} = NT${subtotal:,.0f}")
        st.markdown(f"### 總計：NT${total:,.0f}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➡️ 前往結帳（線上下單）", type="primary"):
                st.session_state.page = "🛒 線上下單"
                st.rerun()
        with c2:
            if st.button("🗑️ 清空購物車"):
                st.session_state.cart = []
                st.rerun()

# ---------- 線上下單 ----------
elif page == "🛒 線上下單":
    st.markdown('<div class="section-title">線上下單與付款</div>', unsafe_allow_html=True)
    cart = st.session_state.cart
    if not cart:
        st.warning("購物車是空的。請先至「📝 組合詢價」選擇產品。")
    else:
        total = sum(item["unit_price"] * item["qty"] for item in cart)
        st.markdown(f"### 🛒 訂單總計：NT${total:,.0f}")
        with st.form("checkout_form"):
            guest_name = st.text_input("聯絡人姓名 *")
            guest_email = st.text_input("Email *")
            guest_phone = st.text_input("電話")
            company = st.text_input("公司名稱")
            note = st.text_area("備註")
            submitted = st.form_submit_button("確認建立訂單")
        
        if submitted:
            if not guest_name or not guest_email:
                st.error("請填寫姓名與 Email")
            else:
                first = cart[0]
                note_full = "[購物車明細]\n" + "\n".join(f"{i['name']} × {i['qty']}" for i in cart) + (f"\n備註：{note}" if note else "")
                payload = {
                    "room_id": first["room_id"],
                    "guest_name": guest_name,
                    "guest_email": guest_email,
                    "guest_phone": guest_phone,
                    "check_in": date.today().isoformat(),
                    "check_out": (date.today() + timedelta(days=7)).isoformat(),
                    "note": note_full,
                    "quantity": sum(i["qty"] for i in cart),
                    "total_amount": total,
                }
                ok, res = api_create_booking(payload)
                if ok:
                    b = res["booking"]
                    st.success(f"✅ 訂單 #{b['id']} 建立成功！")
                    st.session_state.cart = []
                    
                    # 產生綠界付款連結
                    ok_pay, pay_res = api_ecpay_create_order(b["id"])
                    if ok_pay and "redirect_url" in pay_res:
                        pay_url = f"{API_BASE}{pay_res['redirect_url']}"
                        st.markdown(
                            f'<a href="{pay_url}" target="_blank" style="display:inline-block;padding:12px 24px;background:#635BFF;color:#fff;border-radius:8px;text-decoration:none;font-weight:bold;margin-top:10px;">👉 點此前往綠界付款頁面</a>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.info("訂單已成立，您可以至後端管理系統或聯絡客服完成付款。")
                else:
                    st.error(f"建立訂單失敗：{res.get('error')}")

# ---------- 相片瀏覽 ----------
elif page == "📷 相片瀏覽":
    st.markdown('<div class="section-title">本機相片瀏覽</div>', unsafe_allow_html=True)
    image_dir = "images"
    if os.path.exists(image_dir):
        img_files = []
        for root, dirs, files in os.walk(image_dir):
            for f in files:
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    img_files.append((f, os.path.join(root, f)))
        if img_files:
            st.success(f"成功找到 {len(img_files)} 張圖片！")
            for i in range(0, len(img_files), 3):
                cols3 = st.columns(3)
                for idx, (img_name, img_path) in enumerate(img_files[i:i+3]):
                    with cols3[idx]:
                        st.image(img_path, caption=img_name, use_column_width=True)
        else:
            st.warning("找不到圖片。")
    else:
        st.error("找不到 images 資料夾。")