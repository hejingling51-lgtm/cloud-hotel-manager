# hotel_app.py
import os
from datetime import date, timedelta
import requests
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:5000")

st.set_page_config(
    page_title="Gabriel-JL 雲端",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.main .block-container {padding-top: 4rem; max-width: 1200px;}
.section-title {
    font-size: 1.5rem; font-weight: 700; color: #1a1a2e;
    margin: 24px 0 12px; padding-left: 12px;
    border-left: 5px solid #e94560;
}
</style>
""", unsafe_allow_html=True)

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

def api_get_rooms():
    res = _get("/api/rooms", [])
    return res if isinstance(res, list) else []

def api_get_bookings():
    res = _get("/api/bookings", [])
    return res if isinstance(res, list) else []

def api_ecpay_config():
    return _get("/api/ecpay/config", {"configured": False}, timeout=5)

def api_ecpay_create_order(booking_id):
    return _post("/api/ecpay/create-order", {"booking_id": booking_id}, timeout=10)

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
    ("🛒 線上下單", cols[5]), ("💳 綠界 ECPay", cols[6]),
]
for label, col in nav_items:
    with col:
        if st.button(label, key=f"nav_{label}"):
            st.session_state.page = label
            st.rerun()

page = st.session_state.page

if page == "🏠 首頁":
    st.markdown('<div class="section-title">熱門產品</div>', unsafe_allow_html=True)
    rooms = api_get_rooms()
    if rooms:
        cols4 = st.columns(4)
        for j, r in enumerate(rooms[:4]):
            with cols4[j]:
                st.write(f"**{r['room_no']} {r['room_type']}**")
                st.write(f"NT${r['nightly_rate']:.0f}")

elif page == "📝 組合詢價":
    st.markdown('<div class="section-title">組合詢價</div>', unsafe_allow_html=True)
    rooms = api_get_rooms()
    if rooms:
        for r in rooms:
            key = f"qty_{r['id']}"
            if key not in st.session_state:
                st.session_state[key] = 0

        for r in rooms:
            key = f"qty_{r['id']}"
            c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
            with c1:
                st.write(f"**{r['room_no']} {r['room_type']}** (NT${r['nightly_rate']:.0f})")
            with c2:
                if st.button("−", key=f"m_{r['id']}") and st.session_state[key] > 0:
                    st.session_state[key] -= 1
                    st.rerun()
            with c3:
                st.write(f"**{st.session_state[key]}**")
            with c4:
                if st.button("+", key=f"p_{r['id']}"):
                    st.session_state[key] += 1
                    st.rerun()

        selected = [(r, st.session_state[f"qty_{r['id']}"]) for r in rooms if st.session_state[f"qty_{r['id']}"] > 0]
        if selected and st.button("✅ 加入購物車", type="primary"):
            for r, qty in selected:
                st.session_state.cart.append({
                    "room_id": r["id"],
                    "name": f"{r['room_no']} {r['room_type']}",
                    "unit_price": r["nightly_rate"],
                    "qty": qty
                })
                st.session_state[f"qty_{r['id']}"] = 0
            st.success("已加入購物車！")
            st.rerun()

elif page == "🛒 購物車":
    st.markdown('<div class="section-title">購物車</div>', unsafe_allow_html=True)
    cart = st.session_state.cart
    if not cart:
        st.info("購物車是空的。")
    else:
        total = sum(i["unit_price"] * i["qty"] for i in cart)
        for item in cart:
            st.write(f"- {item['name']} × {item['qty']} = NT${item['unit_price'] * item['qty']:,.0f}")
        st.markdown(f"### 總計：NT${total:,.0f}")
        if st.button("➡️ 前往結帳", type="primary"):
            st.session_state.page = "🛒 線上下單"
            st.rerun()

elif page == "🛒 線上下單":
    st.markdown('<div class="section-title">線上下單與付款</div>', unsafe_allow_html=True)
    cart = st.session_state.cart
    if not cart:
        st.warning("購物車是空的。")
    else:
        total = sum(item["unit_price"] * item["qty"] for item in cart)
        with st.form("checkout_form"):
            guest_name = st.text_input("聯絡人姓名 *")
            guest_email = st.text_input("Email *")
            guest_phone = st.text_input("電話")
            note = st.text_area("備註")
            submitted = st.form_submit_button("確認建立訂單")

        if submitted:
            if not guest_name or not guest_email:
                st.error("請填寫姓名與 Email")
            else:
                payload = {
                    "guest_name": guest_name,
                    "guest_email": guest_email,
                    "guest_phone": guest_phone,
                    "check_in": date.today().isoformat(),
                    "check_out": (date.today() + timedelta(days=1)).isoformat(),
                    "total_amount": total,
                    "quantity": sum(i["qty"] for i in cart),
                    "note": note,
                    "items": cart  # 傳遞完整的明細陣列
                }
                
                try:
                    r = requests.post(f"{API_BASE}/api/bookings", json=payload, timeout=8)
                    if r.status_code == 201:
                        res = r.json()
                        b = res.get("booking", {})
                        st.success(f"✅ 訂單 #{b.get('id')} 建立成功！")
                        st.session_state.cart = []
                        
                        # 顯示獨立明細
                        st.markdown("#### 📦 訂單明細內容：")
                        for detail in b.get("items", []):
                            st.write(f"- {detail['room_no']} {detail['room_type']} | 單價: NT${detail['unit_price']} × {detail['quantity']} = NT${detail['subtotal']}")
                    else:
                        st.error(f"建立失敗：{r.text}")
                except Exception as e:
                    st.error(f"連線錯誤：{str(e)}")

elif page == "💳 綠界 ECPay":
    st.markdown('<div class="section-title">綠界 ECPay 待付款訂單</div>', unsafe_allow_html=True)
    bookings = api_get_bookings()
    pending = [b for b in bookings if b["payment_status"] == "pending"]
    if not pending:
        st.info("目前沒有待付款訂單。")
    else:
        for b in pending:
            with st.expander(f"訂單 #{b['id']} · {b['guest_name']} · NT${b['total_amount']:,.0f}"):
                st.write(f"**明細：**")
                for item in b.get("items", []):
                    st.write(f"〡 {item['room_no']} {item['room_type']} × {item['quantity']} (單價 NT${item['unit_price']})")
                if st.button(f"💳 產生付款連結 #{b['id']}", key=f"pay_{b['id']}"):
                    ok, res = api_ecpay_create_order(b["id"])
                    if ok and "redirect_url" in res:
                        st.markdown(f'<a href="{API_BASE}{res["redirect_url"]}" target="_blank">👉 點此前往付款</a>', unsafe_allow_html=True)