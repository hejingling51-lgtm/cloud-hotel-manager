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

/* ============ Hero：無框 + 淡海洋 + 海水流動 ============ */
.hero {
    position: relative;
    background: linear-gradient(180deg,
        #e0f7fa 0%,
        #b2ebf2 40%,
        #4fc3f7 70%,
        #0288d1 100%);
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
    background:
        radial-gradient(ellipse at 20% 100%, rgba(255,255,255,0.35) 0%, transparent 60%),
        radial-gradient(ellipse at 70% 100%, rgba(255,255,255,0.25) 0%, transparent 60%);
    animation: waveShift 6s ease-in-out infinite alternate;
    pointer-events: none;
}
@keyframes waveShift {
    0%   { transform: translateX(-20px); }
    100% { transform: translateX(20px); }
}

/* 三隻鴨子：右下角、大中小 */
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
    0%, 100% { transform: translateY(0)    rotate(-4deg); }
    50%      { transform: translateY(-6px) rotate(4deg);  }
}

/* ============ 一般產品卡片 ============ */
.prod-card {
    border: 1px solid #eee; border-radius: 16px;
    padding: 22px; text-align: center; background: #fff;
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
    background:#fff5f7;border:2px solid #e94560;
    border-radius:12px;padding:20px;text-align:center;margin-top:16px;
}
.total-box .label {color:#888;font-size:0.95rem;}
.total-box .amount {color:#e94560;font-size:2.2rem;font-weight:800;}
</style>
""", unsafe_allow_html=True)


# ============================================================
#  API
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


def api_get_rooms():
    return _get("/api/rooms", [])


def api_set_room_status(room_id, status):
    ok, _ = _post(f"/api/rooms/{room_id}/status", {"status": status})
    return ok


def api_get_bookings():
    return _get("/api/bookings", [])


def api_create_booking(payload):
    try:
        r = requests.post(f"{API_BASE}/api/bookings", json=payload, timeout=8)
        return r.status_code == 201, r.json()
    except Exception as e:
        return False, {"error": str(e)}


def api_update_booking(bid, **kw):
    return _post(f"/api/bookings/{bid}/status", kw)


def api_ecpay_config():
    return _get("/api/ecpay/config", {"configured": False}, timeout=5)


def api_ecpay_create_order(booking_id):
    return _post("/api/ecpay/create-order",
                 {"booking_id": booking_id}, timeout=10)


def api_get_visits():
    return _get("/api/visits", {"count": 0}, timeout=5).get("count", 0)


def api_inc_visits():
    ok, res = _post("/api/visits", None, timeout=5)
    return res.get("count", 0) if ok else 0


# ============================================================
#  訪問計數
# ============================================================
if "visited" not in st.session_state:
    st.session_state.visited = True
    visit_count = api_inc_visits()
else:
    visit_count = api_get_visits()


# ============================================================
#  頁面狀態
# ============================================================
if "page" not in st.session_state:
    st.session_state.page = "🏠 首頁"
if "cart" not in st.session_state:
    st.session_state.cart = []

ADMIN_PAGES = ["📦 產品庫存看板", "📋 訂單管理", "🚚 出貨 / 收貨",
               "💰 帳單與收款", "📑 RFQ 管理", "⚙️ 綠界設定"]


# ============================================================
#  頂部導航
# ============================================================
cols = st.columns([2, 1, 1, 1, 1, 1, 1])
with cols[0]:
    st.markdown(
        "<div style='font-weight:700;font-size:1.2rem;"
        "color:#ffffff;background:#1f6feb;"
        "padding:8px 16px;border-radius:8px;"
        "display:inline-block;'>🏢 Gabriel-JL 雲端企業官網</div>",
        unsafe_allow_html=True,
    )
nav_items = [
    ("🏠 首頁", cols[1]), ("🛍️ 產品介紹", cols[2]),
    ("📝 組合詢價", cols[3]), ("🛒 購物車", cols[4]),
    ("🛒 線上下單", cols[5]),
]
for label, col in nav_items:
    with col:
        if st.button(label, use_container_width=True, key=f"nav_{label}"):
            st.session_state.page = label
            st.rerun()

with cols[6]:
    if st.button("🔐 管理", use_container_width=True, key="nav_admin"):
        st.session_state.show_admin = not st.session_state.get("show_admin", False)
        st.rerun()


# ============================================================
#  管理員登入
# ============================================================
is_admin = False
if st.session_state.get("show_admin", False):
    with st.sidebar:
        st.markdown("### 🔐 員工登入")
        pwd = st.text_input("密碼", type="password", key="admin_pwd")
        expected = ""
        try:
            expected = st.secrets.get("admin", {}).get("password", "")
        except Exception:
            expected = ""
        if pwd and expected and pwd == expected:
            is_admin = True
            st.success("✅ 已登入")
        elif pwd:
            st.error("密碼錯誤")
        if is_admin:
            st.markdown("---")
            st.markdown("### 📋 管理選單")
            for p in ADMIN_PAGES:
                if st.button(p, use_container_width=True, key=f"admin_{p}"):
                    st.session_state.page = p
                    st.rerun()
        st.markdown("---")
        st.caption(f"👀 瀏覽次數：**{visit_count:,}**")


# ============================================================
#  頁面路由
# ============================================================
page = st.session_state.page

# ---------- 首頁 ----------
if page == "🏠 首頁":
    st.markdown("""
    <div class="hero">
      <div class="ducks">
        <span>🦆</span><span>🦆</span><span>🦆</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">熱門產品</div>',
                unsafe_allow_html=True)
    rooms = api_get_rooms()
    if rooms:
        cols4 = st.columns(4)
        for i, r in enumerate(rooms[:4]):
            with cols4[i]:
                st.markdown(f"""
                <div class="prod-card">
                  <h4>{r['room_no']}</h4>
                  <p class="spec">{r['room_type']} · 規格 {r['capacity']}</p>
                  <p class="price">NT${r['nightly_rate']:.0f}
                     <span>/ 單位</span></p>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("""
    <div class="footer">
      © 2026 雲端企業官網 · B2B 採購平台　|　
      綠界 ECPay 金流串接　|　Powered by Streamlit + Flask + PostgreSQL
    </div>
    """, unsafe_allow_html=True)


# ---------- 產品介紹 ----------
elif page == "🛍️ 產品介紹":
    st.markdown('<div class="section-title">產品介紹</div>',
                unsafe_allow_html=True)
    st.caption("可至「📝 組合詢價」用 − / + 調整數量並即時試算總價。")

    rooms = api_get_rooms()
    if not rooms:
        st.warning("無法讀取產品資料，請確認後端 API 是否運行。")
    else:
        types = {}
        for r in rooms:
            types.setdefault(r["room_type"], []).append(r)
        for ptype, items in types.items():
            st.markdown(f"#### {ptype}")
            st.caption(f"共 {len(items)} 款規格")
            for i in range(0, len(items), 3):
                cols3 = st.columns(3)
                for j, p in enumerate(items[i:i + 3]):
                    with cols3[j]:
                        st.markdown(f"""
                        <div class="prod-card">
                          <h4>{p['room_no']}</h4>
                          <p class="spec">{p['room_type']} · 規格 {p['capacity']}</p>
                          <p class="price">NT${p['nightly_rate']:.0f}
                             <span>/ 單位</span></p>
                        </div>
                        """, unsafe_allow_html=True)


# ---------- 組合詢價 ----------
elif page == "📝 組合詢價":
    st.markdown('<div class="section-title">組合詢價</div>',
                unsafe_allow_html=True)
    st.caption("點選 − / + 調整數量，系統即時試算總價。價格滿意即可加入購物車。")

    rooms = api_get_rooms()
    if not rooms:
        st.warning("無法讀取產品資料。")
    else:
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
                st.markdown(
                    f"**{r['room_no']} {r['room_type']}**　"
                    f"<span style='color:#888;'>NT${r['nightly_rate']:.0f}/單位</span>",
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("−", key=f"minus_{r['id']}", use_container_width=True):
                    if st.session_state[key] > 0:
                        st.session_state[key] -= 1
                    st.rerun()
            with c3:
                st.markdown(
                    f"<div style='text-align:center;font-size:1.3rem;"
                    f"font-weight:700;padding-top:6px;'>{qty}</div>",
                    unsafe_allow_html=True,
                )
            with c4:
                if st.button("+", key=f"plus_{r['id']}", use_container_width=True):
                    st.session_state[key] += 1
                    st.rerun()
            with c5:
                if qty > 0:
                    st.markdown(
                        f"<div style='text-align:right;color:#e94560;"
                        f"font-weight:700;padding-top:6px;'>"
                        f"NT${subtotal:,.0f}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='text-align:right;color:#ccc;padding-top:6px;'>—</div>",
                        unsafe_allow_html=True,
                    )
            st.markdown(
                "<hr style='margin:6px 0;border:none;border-top:1px solid #f0f0f0;'>",
                unsafe_allow_html=True,
            )

        selected = [(r, st.session_state[f"qty_{r['id']}"])
                    for r in rooms if st.session_state[f"qty_{r['id']}"] > 0]

        if not selected:
            st.info("尚未選擇任何產品，請用上方 − / + 調整數量。")
        else:
            st.markdown("### 🧾 組合試算")
            total = 0
            for r, qty in selected:
                subtotal = r["nightly_rate"] * qty
                total += subtotal
                st.markdown(f"- {r['room_no']} {r['room_type']} × {qty} = NT${subtotal:,.0f}")
            st.markdown(
                f"<div class='total-box'>"
                f"<div class='label'>組合總計</div>"
                f"<div class='amount'>NT${total:,.0f}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("")
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                if st.button("✅ 價格 OK，加入購物車",
                             type="primary", use_container_width=True):
                    for r, qty in selected:
                        found = False
                        for item in st.session_state.cart:
                            if item["room_id"] == r["id"]:
                                item["qty"] += qty
                                found = True
                                break
                        if not found:
                            st.session_state.cart.append({
                                "room_id": r["id"],
                                "name": f"{r['room_no']} {r['room_type']}",
                                "unit_price": r["nightly_rate"],
                                "qty": qty,
                            })
                    for r in rooms:
                        st.session_state[f"qty_{r['id']}"] = 0
                    st.success(f"✅ 已加入購物車（NT${total:,.0f}）")
                    st.rerun()
            with c2:
                if st.button("🗑️ 清空組合", use_container_width=True):
                    for r in rooms:
                        st.session_state[f"qty_{r['id']}"] = 0
                    st.rerun()
            with c3:
                cart_count = sum(i["qty"] for i in st.session_state.cart)
                if st.button(f"🛒 購物車（{cart_count}）",
                             use_container_width=True):
                    st.session_state.page = "🛒 購物車"
                    st.rerun()

        if st.session_state.cart:
            st.markdown("---")
            st.markdown("### 🛒 購物車預覽")
            cart_total = 0
            for item in st.session_state.cart:
                subtotal = item["unit_price"] * item["qty"]
                cart_total += subtotal
                st.write(f"- {item['name']} × {item['qty']} = NT${subtotal:,.0f}")
            st.markdown(f"**購物車總計：NT${cart_total:,.0f}**")
            if st.button("➡️ 前往購物車", type="primary"):
                st.session_state.page = "🛒 購物車"
                st.rerun()


# ---------- 購物車 ----------
elif page == "🛒 購物車":
    st.markdown('<div class="section-title">購物車</div>',
                unsafe_allow_html=True)
    cart = st.session_state.cart
    if not cart:
        st.info("購物車是空的，請至「📝 組合詢價」選擇產品。")
    else:
        total = 0
        for i, item in enumerate(cart):
            subtotal = item["unit_price"] * item["qty"]
            total += subtotal
            c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 2])
            with c1:
                st.write(f"**{item['name']}**（NT${item['unit_price']:.0f}/單位）")
            with c2:
                if st.button("−", key=f"c_minus_{i}", use_container_width=True):
                    if item["qty"] > 1:
                        item["qty"] -= 1
                    else:
                        cart.pop(i)
                    st.rerun()
            with c3:
                st.markdown(
                    f"<div style='text-align:center;font-size:1.3rem;"
                    f"font-weight:700;padding-top:6px;'>{item['qty']}</div>",
                    unsafe_allow_html=True,
                )
            with c4:
                if st.button("+", key=f"c_plus_{i}", use_container_width=True):
                    item["qty"] += 1
                    st.rerun()
            with c5:
                st.markdown(
                    f"<div style='text-align:right;color:#e94560;"
                    f"font-weight:700;padding-top:6px;'>NT${subtotal:,.0f}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                "<hr style='margin:6px 0;border:none;border-top:1px solid #f0f0f0;'>",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<div class='total-box'>"
            f"<div class='label'>購物車總計</div>"
            f"<div class='amount'>NT${total:,.0f}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➡️ 前往結帳", type="primary", use_container_width=True):
                st.session_state.page = "🛒 線上下單"
                st.rerun()
        with c2:
            if st.button("🗑️ 清空購物車", use_container_width=True):
                st.session_state.cart = []
                st.rerun()


# ---------- 線上下單 ----------
elif page == "🛒 線上下單":
    st.markdown('<div class="section-title">線上下單</div>',
                unsafe_allow_html=True)
    st.caption("確認購物車內容並填寫聯絡資訊，系統將建立訂單並引導至綠界付款。")
    cart = st.session_state.cart
    if not cart:
        st.warning("購物車是空的。請先至「📝 組合詢價」選擇產品。")
    else:
        st.markdown("### 🛒 訂單內容")
        total = 0
        for item in cart:
            subtotal = item["unit_price"] * item["qty"]
            total += subtotal
            st.write(f"- {item['name']} × {item['qty']} = NT${subtotal:,.0f}")
        st.markdown(
            f"<div class='total-box'>"
            f"<div class='label'>訂單總計</div>"
            f"<div class='amount'>NT${total:,.0f}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown("### 📋 聯絡資訊")
        with st.form("checkout"):
            c1, c2 = st.columns(2)
            with c1:
                guest_name = st.text_input("聯絡人姓名 *")
                guest_email = st.text_input("Email *")
                guest_phone = st.text_input("電話")
            with c2:
                company = st.text_input("公司名稱")
                tax_id = st.text_input("統一編號")
                delivery = st.date_input("希望交期", value=date.today() + timedelta(days=7))
            note = st.text_area("備註（規格、包裝、發票等）", height=80)
            submitted = st.form_submit_button("建立訂單")
        if submitted:
            if not guest_name or not guest_email:
                st.error("聯絡人與 Email 必填")
            else:
                first = cart[0]
                note_full = (
                    "[購物車明細]\n"
                    + "\n".join(f"{i['name']} × {i['qty']}" for i in cart)
                    + (f"\n公司：{company}" if company else "")
                    + (f"\n統編：{tax_id}" if tax_id else "")
                    + (f"\n備註：{note}" if note else "")
                )
                payload = {
                    "room_id": first["room_id"],
                    "guest_name": guest_name,
                    "guest_email": guest_email,
                    "guest_phone": guest_phone,
                    "check_in": date.today().isoformat(),
                    "check_out": delivery.isoformat(),
                    "note": note_full,
                    "quantity": sum(i["qty"] for i in cart),
                    "total_amount": total,
                }
                ok, res = api_create_booking(payload)
                if ok:
                    b = res["booking"]
                    st.success(f"✅ 訂單 #{b['id']} 已建立，金額 NT${b['total_amount']:,.0f}")
                    st.session_state.cart = []
                    st.session_state["last_booking_id"] = b["id"]
                    st.info("請至「💰 帳單與收款」完成付款。")
                else:
                    st.error(f"建立失敗：{res.get('error')}")


# ---------- 聯絡我們 ----------
elif page == "📞 聯絡我們":
    st.markdown('<div class="section-title">聯絡我們</div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("""
        ### 業務洽詢
        - 📞 電話：02-25500684, 0928185292
        - 📧 Email：hejingling51@gmail.com
        - 🏢 地址：台北市大同區寧夏路20號9樓
        - 🕘 服務時間：週一至週五 09:00 - 18:00
        """)
    with c2:
        st.markdown("""
        ### 大量採購 / 客製需求
        請使用「📝 組合詢價」功能，即時試算組合價格，滿意的話直接加入購物車結帳。
        若已有訂單需要付款，請至「💰 帳單與收款」頁面。
        """)


# ============================================================
#  管理員頁面
# ============================================================

# ---------- 產品庫存看板 ----------
elif page == "📦 產品庫存看板":
    if not is_admin:
        st.error("請先登入管理員帳號（點右上角 🔐 管理）")
    else:
        rooms = api_get_rooms()
        if not rooms:
            st.warning("無法讀取產品資料。")
        else:
            st.markdown(f"### 共 {len(rooms)} 筆產品")
            status_color = {
                "available": "🟢 有貨", "occupied": "🔴 出貨中",
                "cleaning": "🟡 補貨中", "maintenance": "⚫ 停售",
            }
            for i in range(0, len(rooms), 4):
                cols4 = st.columns(4)
                for j, r in enumerate(rooms[i:i + 4]):
                    with cols4[j]:
                        color = status_color.get(r["status"], r["status"])
                        st.markdown(f"""
                        <div class="prod-card">
                          <h4>{r['room_no']}</h4>
                          <p class="spec">{r['room_type']}</p>
                          <p class="price">NT${r['nightly_rate']:.0f}</p>
                          <p>{color}</p>
                        </div>
                        """, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("### 🔧 快速修改庫存狀態")
            room_opts = {f"{r['room_no']} ({r['room_type']})": r["id"] for r in rooms}
            sel = st.selectbox("選擇產品", list(room_opts.keys()))
            new_status = st.selectbox(
                "新狀態",
                ["available", "occupied", "cleaning", "maintenance"],
                format_func=lambda x: status_color[x],
            )
            if st.button("更新狀態"):
                if api_set_room_status(room_opts[sel], new_status):
                    st.success("✅ 已更新")
                    st.rerun()
                else:
                    st.error("更新失敗")


# ---------- 訂單管理 ----------
elif page == "📋 訂單管理":
    if not is_admin:
        st.error("請先登入管理員帳號（點右上角 🔐 管理）")
    else:
        bookings = api_get_bookings()
        st.markdown("### 📋 訂單列表")
        if not bookings:
            st.info("尚無訂單")
        else:
            df = pd.DataFrame([{
                "ID": b["id"], "產品": b["room_id"], "聯絡人": b["guest_name"],
                "下單日": b["check_in"], "交期": b["check_out"],
                "數量": b["nights"], "金額": f"NT${b['total_amount']:,.0f}",
                "付款": b["payment_status"], "狀態": b["booking_status"],
            } for b in bookings])
            st.dataframe(df, use_container_width=True, hide_index=True)


# ---------- 出貨 / 收貨 ----------
elif page == "🚚 出貨 / 收貨":
    if not is_admin:
        st.error("請先登入管理員帳號（點右上角 🔐 管理）")
    else:
        bookings = api_get_bookings()
        if not bookings:
            st.info("尚無訂單")
        else:
            st.markdown("### 🚚 出貨 / 收貨 操作")
            for b in bookings:
                if b["booking_status"] in ("cancelled", "checked_out"):
                    continue
                with st.expander(
                    f"#{b['id']} · {b['guest_name']} · "
                    f"產品 {b['room_id']} · {b['booking_status']}"
                ):
                    cols3 = st.columns(3)
                    with cols3[0]:
                        if b["booking_status"] == "reserved" and st.button(
                            "✅ 確認出貨", key=f"ship_{b['id']}"
                        ):
                            ok, _ = api_update_booking(
                                b["id"], booking_status="checked_in")
                            if ok:
                                st.success("已出貨")
                                st.rerun()
                    with cols3[1]:
                        if b["booking_status"] == "checked_in" and st.button(
                            "📦 確認收貨", key=f"recv_{b['id']}"
                        ):
                            ok, _ = api_update_booking(
                                b["id"], booking_status="checked_out")
                            if ok:
                                st.success("已收貨")
                                st.rerun()
                    with cols3[2]:
                        if b["booking_status"] == "reserved" and st.button(
                            "❌ 取消訂單", key=f"cx_{b['id']}"
                        ):
                            ok, _ = api_update_booking(
                                b["id"], booking_status="cancelled")
                            if ok:
                                st.success("已取消")
                                st.rerun()


# ---------- 帳單與收款 ----------
elif page == "💰 帳單與收款":
    if not is_admin:
        st.error("請先登入管理員帳號（點右上角 🔐 管理）")
    else:
        cfg = api_ecpay_config()
        if not cfg.get("configured"):
            st.error("⚠️ 綠界 ECPay 尚未設定，請先至「⚙️ 綠界設定」頁面確認。")
        bookings = api_get_bookings()
        pending = [b for b in bookings
                   if b["payment_status"] == "pending"
                   and b["booking_status"] != "cancelled"]
        st.markdown("### 💳 待付款訂單")
        if not pending:
            st.info("目前沒有待付款訂單")
        else:
            for b in pending:
                with st.expander(
                    f"#{b['id']} · {b['guest_name']} · NT${b['total_amount']:,.0f}"
                ):
                    st.write(f"**產品：** {b['room_id']}")
                    st.write(f"**交期：** {b['check_out']}")
                    st.write(f"**數量：** {b['nights']}")
                    st.write(f"**聯絡人：** {b['guest_email']}")
                    if b.get("note"):
                        st.text(b["note"])
                    if b.get("stripe_session_id"):
                        st.caption(f"綠界交易編號：`{b['stripe_session_id']}`")
                    if st.button(
                        f"💳 產生綠界付款連結 #{b['id']}",
                        key=f"pay_{b['id']}"
                    ):
                        ok, res = api_ecpay_create_order(b["id"])
                        if ok:
                            redirect_url = f"{API_BASE}{res['redirect_url']}"
                            st.session_state[f"ecpay_url_{b['id']}"] = redirect_url
                            st.success("✅ 付款表單已產生")
                        else:
                            st.error(f"建立訂單失敗：{res.get('error')}")
                    url_key = f"ecpay_url_{b['id']}"
                    if url_key in st.session_state:
                        st.markdown(
                            f'<a href="{st.session_state[url_key]}" '
                            f'target="_blank" style="display:inline-block;'
                            f'padding:12px 24px;background:#635BFF;'
                            f'color:#fff;border-radius:8px;'
                            f'text-decoration:none;font-weight:bold;'
                            f'margin-top:8px;">'
                            f'👉 點此前往綠界付款頁面</a>',
                            unsafe_allow_html=True,
                        )
                        st.caption(f"連結：{st.session_state[url_key]}")
        st.markdown("---")
        st.markdown("### 📊 收款總覽")
        if bookings:
            total_paid = sum(b["total_amount"] for b in bookings
                             if b["payment_status"] == "paid")
            total_pending = sum(b["total_amount"] for b in bookings
                                if b["payment_status"] == "pending")
            c1, c2, c3 = st.columns(3)
            c1.metric("已收款", f"NT${total_paid:,.0f}")
            c2.metric("待收款", f"NT${total_pending:,.0f}")
            c3.metric("訂單總數", len(bookings))


# ---------- RFQ 管理 ----------
elif page == "📑 RFQ 管理":
    if not is_admin:
        st.error("請先登入管理員帳號（點右上角 🔐 管理）")
    else:
        st.markdown("### 📑 RFQ 詢價單管理")
        st.info("目前購物車儲存在瀏覽器 session，尚未啟用資料庫 RFQ 功能。")


# ---------- 綠界設定 ----------
# ---------- 綠界設定 ----------
elif page == "⚙️ 綠界設定":
    if not is_admin:
        st.error("請先登入管理員帳號（點右上角 🔐 管理）")
    else:
        st.markdown("### ⚙️ 綠界 ECPay 設定檢查")
        cfg = api_ecpay_config()
        if cfg.get("configured"):
            st.success("✅ 綠界 ECPay 已設定完成")
        else:
            st.error("❌ 綠界 ECPay 尚未設定，請檢查後端環境變數")
        st.markdown("#### 目前設定")
        st.write(f"**API URL：** `{cfg.get('api_url', '未設定')}`")
        st.write(f"**MerchantID：** `{cfg.get('merchant_id', '未設定')}`")
        st.markdown("---")
        st.markdown("#### 後端環境變數清單")
        st.code("""
ECPAY_MERCHANT_ID=你的特店編號
ECPAY_HASH_KEY=你的HashKey
ECPAY_HASH_IV=你的HashIV
ECPAY_API_URL=https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5
ECPAY_RETURN_URL=https://your-domain.com/api/ecpay/notify
""", language="bash")
        st.info(
            "ℹ️ 正式上線前，請向綠界申請正式特約商店帳號，"
            "並將 ECPAY_API_URL 改為正式環境：\n"
            "`https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5`"
        )