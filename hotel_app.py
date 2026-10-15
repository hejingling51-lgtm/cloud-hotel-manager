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
    background:#fff5f7;border:2px solid #e94560;
    border-radius:12px;padding:20px;text-align:center;margin-top:16px;
}
.total-box .label {color:#888;font-size:0.95rem;}
.total-box .amount {color:#e94560;font-size:2.2rem;font-weight:800;}
</style>
""", unsafe_allow_html=True)


# ============================================================
#  API 與資料處理輔助 (含強固防呆)
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
    """強固的產品資料處理與防呆保護，確保不論 API 回傳格式如何都不會崩潰"""
    processed = []
    if not isinstance(rooms, list):
        rooms = [
            {"id": 1, "room_no": "R0001", "room_type": "成人襪", "capacity": 2, "nightly_rate": 280, "status": "available"},
            {"id": 2, "room_no": "R0002", "room_type": "成人襪", "capacity": 2, "nightly_rate": 280, "status": "available"},
            {"id": 13, "room_no": "R0013", "room_type": "兒童襪", "capacity": 2, "nightly_rate": 250, "status": "available"},
            {"id": 14, "room_no": "R0014", "room_type": "兒童襪", "capacity": 2, "nightly_rate": 250, "status": "available"},
        ]
        
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
            r_copy["capacity"] = int(r_copy.get("capacity", 2) or 2)
            r_copy["status"] = r_copy.get("status", "available")
            r_copy["id"] = r_copy.get("id", num)
        except Exception:
            r_copy["nightly_rate"] = 280.0
            r_copy["capacity"] = 2
            r_copy["room_type"] = "成人襪"
            r_copy["status"] = "available"
        processed.append(r_copy)
    return processed


def api_get_rooms():
    try:
        r = requests.get(f"{API_BASE}/api/rooms", timeout=5)
        if r.ok:
            data = r.json()
            if isinstance(data, list):
                return process_rooms(data)
    except Exception:
        pass
    return process_rooms([])


def api_set_room_status(room_id, status):
    ok, _ = _post(f"/api/rooms/{room_id}/status", {"status": status})
    return ok


def api_get_bookings():
    res = _get("/api/bookings", [])
    return res if isinstance(res, list) else []


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
    return _post("/api/ecpay/create-order", {"booking_id": booking_id}, timeout=10)


def api_get_visits():
    res = _get("/api/visits", {"count": 0}, timeout=5)
    return res.get("count", 0) if isinstance(res, dict) else 0


def api_inc_visits():
    ok, res = _post("/api/visits", None, timeout=5)
    return res.get("count", 0) if ok and isinstance(res, dict) else 0


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
cols = st.columns([1.5, 1, 1, 1, 1, 1, 1, 1])
with cols[0]:
    st.markdown(
        "<div style='font-weight:700;font-size:1.1rem;"
        "color:#1a1a2e;padding-top:6px;'>🏢 Gabriel-JL 雲端</div>",
        unsafe_allow_html=True,
    )
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
IMAGE_DIR = "images"  # 使用專案根目錄下的相對路徑


def get_product_image(room_no):
    """根據產品編號精準抓取 images 資料夾中的圖片（例如 R0013 對應 images/R0013.jpg）"""
    try:
        clean_no = str(room_no).upper().strip()
        if not clean_no.startswith("R"):
            clean_no = f"R{clean_no}"
            
        img_path = os.path.join(IMAGE_DIR, f"{clean_no}.jpg")
        if os.path.exists(img_path):
            return img_path
    except Exception:
        pass
    return None


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
                img_path = get_product_image(r['room_no'])
                if img_path:
                    st.image(img_path, use_container_width=True)
                else:
                    st.info("📷 暫無圖片")

                st.markdown(f"""
                <div class="prod-card" style="border-top:none; border-top-left-radius:0; border-top-right-radius:0;">
                  <h4>{r['room_no']}</h4>
                  <p class="spec">{r['room_type']} · 規格 {r['capacity']}</p>
                  <p class="price">NT${r['nightly_rate']:.0f}
                     <span>/ 單位</span></p>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("""
    <div class="footer">
      © 2026 雲端企業官網 · B2B 採購平台 | 
      綠界 ECPay 金流串接 | Powered by Streamlit + Flask + PostgreSQL
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
                        img_path = get_product_image(p['room_no'])
                        if img_path:
                            st.image(img_path, use_container_width=True)
                        else:
                            st.info("📷 暫無圖片")

                        st.markdown(f"""
                        <div class="prod-card" style="border-top:none; border-top-left-radius:0; border-top-right-radius:0;">
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
                    f"**{r['room_no']} {r['room_type']}** "
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
                        f"font-weight