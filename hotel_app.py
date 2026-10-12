# hotel_app.py
import os
import requests
import streamlit as st
import pandas as pd
from datetime import date, timedelta

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:5000")

st.set_page_config(
    page_title="24 間套房雲端旅店管理",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== API ====================
def api_get_rooms():
    try:
        return requests.get(f"{API_BASE}/api/rooms", timeout=8).json()
    except Exception:
        return []

def api_get_bookings():
    try:
        return requests.get(f"{API_BASE}/api/bookings", timeout=8).json()
    except Exception:
        return []

def api_create_booking(payload):
    try:
        r = requests.post(f"{API_BASE}/api/bookings", json=payload, timeout=8)
        return r.status_code == 201, r.json()
    except Exception as e:
        return False, {"error": str(e)}

def api_set_room_status(room_id, status):
    try:
        r = requests.post(f"{API_BASE}/api/rooms/{room_id}/status",
                          json={"status": status}, timeout=8)
        return r.ok
    except Exception:
        return False

def api_update_booking(bid, **kw):
    try:
        r = requests.post(f"{API_BASE}/api/bookings/{bid}/status",
                          json=kw, timeout=8)
        return r.ok, r.json()
    except Exception as e:
        return False, {"error": str(e)}

# ---------- 绿界 ECPay ----------
def api_ecpay_config():
    try:
        return requests.get(f"{API_BASE}/api/ecpay/config", timeout=5).json()
    except Exception:
        return {"configured": False}

def api_ecpay_create_order(booking_id):
    try:
        r = requests.post(f"{API_BASE}/api/ecpay/create-order",
                          json={"booking_id": booking_id}, timeout=10)
        return r.ok, r.json()
    except Exception as e:
        return False, {"error": str(e)}

def api_ecpay_query(booking_id):
    try:
        r = requests.get(f"{API_BASE}/api/ecpay/query/{booking_id}", timeout=8)
        return r.ok, r.json()
    except Exception as e:
        return False, {"error": str(e)}

# ---------- 访问计数 ----------
def api_get_visits():
    try:
        return requests.get(f"{API_BASE}/api/visits", timeout=5).json().get("count", 0)
    except Exception:
        return 0

def api_inc_visits():
    try:
        return requests.post(f"{API_BASE}/api/visits", timeout=5).json().get("count", 0)
    except Exception:
        return 0

# ==================== 访问计数 ====================
if "visited" not in st.session_state:
    st.session_state.visited = True
    visit_count = api_inc_visits()
else:
    visit_count = api_get_visits()

# ==================== 侧边栏导航 ====================
with st.sidebar:
    st.markdown("### 🏨 24 間套房雲端旅店")
    st.caption(f"👀 瀏覽次數：**{visit_count:,}**")
    st.markdown("---")
    page = st.radio("導航", [
        "📊 房間看板",
        "📅 預訂管理",
        "🛎️ 入住 / 退房",
        "💳 帳單與收款",
        "⚙️ 綠界設定",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.caption("© 2026 Cloud Hotel Management")

st.title("🏨 24 間套房雲端旅店管理系統")

# ==================== 绿界付款回调提示 ====================
qs = st.query_params
if "booking_id" in qs and "ecpay_done" not in st.session_state:
    bid = qs["booking_id"]
    ok, res = api_ecpay_query(bid)
    if ok and res.get("paid"):
        st.success(f"✅ 訂單 #{bid} 已付款完成！")
    else:
        st.info(f"ℹ️ 訂單 #{bid} 付款尚未確認，若剛完成付款請稍後重新整理。")
    st.session_state.ecpay_done = True


# ==================== 1. 房间看板 ====================
if page == "📊 房間看板":
    rooms = api_get_rooms()
    if not rooms:
        st.warning("無法讀取房間資料，請確認後端 API 是否運行。")
    else:
        st.markdown(f"### 共 {len(rooms)} 間套房")
        status_color = {
            "available": "🟢 空閒",
            "occupied": "🔴 入住中",
            "cleaning": "🟡 清潔中",
            "maintenance": "⚫ 維修",
        }
        per_row = 4
        for i in range(0, len(rooms), per_row):
            cols = st.columns(per_row)
            for j, room in enumerate(rooms[i:i+per_row]):
                with cols[j]:
                    color = status_color.get(room["status"], room["status"])
                    st.markdown(f"""
                    <div style="border:2px solid #ccc;border-radius:12px;
                                padding:12px;text-align:center;background:#fff;
                                box-shadow:0 2px 8px rgba(0,0,0,0.08);">
                      <h3 style="margin:0;">{room['room_no']}</h3>
                      <p style="margin:4px 0;color:#666;">{room['room_type']}</p>
                      <p style="margin:4px 0;color:#e94560;font-weight:bold;">
                        ${room['nightly_rate']:.0f}/晚</p>
                      <p style="margin:4px 0;">{color}</p>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔧 快速修改房間狀態")
        room_opts = {f"{r['room_no']} ({r['room_type']})": r["id"] for r in rooms}
        sel = st.selectbox("選擇房間", list(room_opts.keys()))
        new_status = st.selectbox("新狀態",
            ["available", "occupied", "cleaning", "maintenance"],
            format_func=lambda x: status_color[x])
        if st.button("更新狀態"):
            if api_set_room_status(room_opts[sel], new_status):
                st.success("✅ 已更新")
                st.rerun()
            else:
                st.error("更新失敗")


# ==================== 2. 预订管理 ====================
elif page == "📅 預訂管理":
    rooms = api_get_rooms()
    bookings = api_get_bookings()

    st.markdown("### ➕ 新增預訂")
    with st.form("new_booking"):
        c1, c2 = st.columns(2)
        with c1:
            guest_name = st.text_input("客人姓名 *")
            guest_email = st.text_input("Email *")
            guest_phone = st.text_input("電話")
        with c2:
            room_opts = {f"{r['room_no']} - {r['room_type']} (${r['nightly_rate']:.0f}/晚)":
                         r["id"] for r in rooms}
            sel_room = st.selectbox("房間 *", list(room_opts.keys()))
            ci = st.date_input("入住日", value=date.today())
            co = st.date_input("退房日", value=date.today() + timedelta(days=1))
        note = st.text_area("備註", height=80)
        submitted = st.form_submit_button("建立預訂")

    if submitted:
        if not guest_name or not guest_email:
            st.error("姓名與 Email 必填")
        else:
            payload = {
                "room_id": room_opts[sel_room],
                "guest_name": guest_name,
                "guest_email": guest_email,
                "guest_phone": guest_phone,
                "check_in": ci.isoformat(),
                "check_out": co.isoformat(),
                "note": note,
            }
            ok, res = api_create_booking(payload)
            if ok:
                st.success(f"✅ 已建立預訂 #{res['booking']['id']}，"
                           f"金額 ${res['booking']['total_amount']:.2f}")
                st.rerun()
            else:
                st.error(f"建立失敗：{res.get('error')}")

    st.markdown("---")
    st.markdown("### 📋 預訂列表")
    if not bookings:
        st.info("尚無預訂")
    else:
        df = pd.DataFrame([{
            "ID": b["id"],
            "房間": b["room_id"],
            "客人": b["guest_name"],
            "入住": b["check_in"],
            "退房": b["check_out"],
            "晚數": b["nights"],
            "金額": f"${b['total_amount']:.2f}",
            "付款": b["payment_status"],
            "狀態": b["booking_status"],
        } for b in bookings])
        st.dataframe(df, use_container_width=True, hide_index=True)


# ==================== 3. 入住/退房 ====================
elif page == "🛎️ 入住 / 退房":
    bookings = api_get_bookings()
    if not bookings:
        st.info("尚無預訂")
    else:
        st.markdown("### 🛎️ 入住 / 退房 操作")
        for b in bookings:
            if b["booking_status"] in ("cancelled", "checked_out"):
                continue
            with st.expander(f"#{b['id']} · {b['guest_name']} · 房間 {b['room_id']} · "
                             f"{b['check_in']} → {b['check_out']} · {b['booking_status']}"):
                cols = st.columns(3)
                with cols[0]:
                    if b["booking_status"] == "reserved" and st.button(
                            "✅ 辦理入住", key=f"ci_{b['id']}"):
                        ok, _ = api_update_booking(b["id"], booking_status="checked_in")
                        if ok:
                            st.success("已入住")
                            st.rerun()
                with cols[1]:
                    if b["booking_status"] == "checked_in" and st.button(
                            "🚪 辦理退房", key=f"co_{b['id']}"):
                        ok, _ = api_update_booking(b["id"], booking_status="checked_out")
                        if ok:
                            st.success("已退房")
                            st.rerun()
                with cols[2]:
                    if b["booking_status"] == "reserved" and st.button(
                            "❌ 取消預訂", key=f"cx_{b['id']}"):
                        ok, _ = api_update_booking(b["id"], booking_status="cancelled")
                        if ok:
                            st.success("已取消")
                            st.rerun()


# ==================== 4. 账单与收款（绿界 ECPay） ====================
elif page == "💳 帳單與收款":
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
            with st.expander(f"#{b['id']} · {b['guest_name']} · "
                             f"NT${b['total_amount']:.0f}"):
                st.write(f"**房間：** {b['room_id']}")
                st.write(f"**日期：** {b['check_in']} → {b['check_out']} "
                         f"（{b['nights']} 晚）")
                st.write(f"**客人：** {b['guest_email']}")

                if b.get("stripe_session_id"):
                    st.caption(f"綠界交易編號：`{b['stripe_session_id']}`")

                if st.button(f"💳 前往綠界付款 #{b['id']}", key=f"pay_{b['id']}"):
                    ok, res = api_ecpay_create_order(b["id"])
                    if ok:
                        # 用 Flask 中转页 URL，打开新标签页
                        redirect_url = f"{API_BASE}{res['redirect_url']}"
                        st.session_state[f"ecpay_url_{b['id']}"] = redirect_url
                        st.success("✅ 付款表單已產生")
                    else:
                        st.error(f"建立訂單失敗：{res.get('error')}")

                # 若已生成过 URL，显示可点击链接
                url_key = f"ecpay_url_{b['id']}"
                if url_key in st.session_state:
                    st.markdown(
                        f'<a href="{st.session_state[url_key]}" target="_blank" '
                        f'style="display:inline-block;padding:12px 24px;'
                        f'background:#635BFF;color:#fff;border-radius:8px;'
                        f'text-decoration:none;font-weight:bold;'
                        f'margin-top:8px;">'
                        f'👉 點此前往綠界付款頁面</a>',
                        unsafe_allow_html=True,
                    )
                    st.info("💡 若沒自動開啟新視窗，請手動複製上方連結，"
                            "或長按連結選擇「在新分頁中開啟」。")
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


# ==================== 5. 绿界设定 ====================
elif page == "⚙️ 綠界設定":
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
ECPAY_CLIENT_BACK_URL=https://your-domain.com
""", language="bash")

    st.markdown("---")
    st.markdown("#### 綠界測試環境憑證（僅供開發測試）")
    st.code("""
MerchantID: 3002607
HashKey:    pwFHCqoQZGmho4w6
HashIV:     EkRm7iFT261dpevs

測試信用卡：4311-9522-2222-2222
有效期限：任意未來日期
CVV：任意三位數
""", language="text")

    st.info(
        "ℹ️ 正式上線前，請向綠界申請正式特約商店帳號，"
        "並將 ECPAY_API_URL 改為正式環境：\n"
        "`https://payment.ecpay.com.tw/Cashier/AioCheckOut/V5`"
    )

    st.markdown("---")
    st.markdown("#### 重要注意事項")
    st.markdown("""
- **ReturnURL** 必須是對外可訪問的 HTTPS 網址，本機開發需用 ngrok / cloudflared 之類的工具
- **ReturnURL** 收到的 POST 回應必須是純字串 `1|OK`，否則綠界會持續重送
- **TotalAmount** 必須為整數（新台幣元），綠界不接受小數
- 收海外信用卡需向綠界申請 **特約賣家** 資格
- 付款頁面必須在**瀏覽器頂層視窗**開啟，不能在 Streamlit 的 iframe 裡
""")