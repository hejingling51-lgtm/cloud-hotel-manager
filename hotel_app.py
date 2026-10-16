# hotel_app.py
import os
from datetime import date, timedelta
import requests
import streamlit as st

API_BASE = os.environ.get("API_BASE", "https://cloud-hotel-manager-1.onrender.com")

st.set_page_config(
    page_title="Gabriel-JL ?²ç«¯",
    page_icon="?¢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
#  CSS æ¨??è¨­å? (æµ·æ??•ç•« + ä¸‰éš»é´¨å?)
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

/* ?? ä¸‰éš»é´¨å? */
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
</style>
""", unsafe_allow_html=True)

# ============================================================
#  API ?‡è??©å‡½å¼?
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


def process_products(products):
    """?´ç??†å?è³‡æ?ï¼Œè‹¥ç©ºå??å‚³ 20 ç­†é?è¨­å??ã€?""
    if not isinstance(products, list) or len(products) == 0:
        products = []
        for i in range(1, 21):
            product_no = f"R{i:04d}"
            if i <= 12:
                product_type = "?äººè¥?
                price = 280
            else:
                product_type = "?’ç«¥è¥?
                price = 250
            products.append({
                "id": i,
                "product_no": product_no,
                "product_type": product_type,
                "spec": "1",
                "unit_price": price,
                "stock_status": "available",
            })
    processed = []
    for p in products:
        if not isinstance(p, dict):
            continue
        p_copy = p.copy()
        try:
            product_no_str = str(p_copy.get("product_no", "R0001"))
            digits = ''.join(filter(str.isdigit, product_no_str))
            num = int(digits) if digits else 1
            p_copy["product_no"] = f"R{num:04d}"

            if 13 <= num <= 20:
                p_copy["product_type"] = "?’ç«¥è¥?
            else:
                p_copy["product_type"] = p_copy.get("product_type", "?äººè¥?)

            p_copy["unit_price"] = float(p_copy.get("unit_price", 280) or 280)
            p_copy["spec"] = str(p_copy.get("spec", "1") or "1")
            p_copy["stock_status"] = "available"
            p_copy["id"] = p_copy.get("id", num)
        except Exception:
            p_copy["unit_price"] = 280.0
            p_copy["spec"] = "1"
            p_copy["product_type"] = "?äººè¥?
            p_copy["stock_status"] = "available"
        processed.append(p_copy)
    return processed


def api_get_products():
    try:
        r = requests.get(f"{API_BASE}/api/products", timeout=3)
        if r.ok:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return process_products(data)
    except Exception:
        pass
    return process_products([])


def api_get_orders():
    res = _get("/api/orders", [])
    return res if isinstance(res, list) else []


def api_ecpay_config():
    return _get("/api/ecpay/config", {"configured": False}, timeout=5)


def api_ecpay_create_order(order_id):
    return _post("/api/ecpay/create-order", {"order_id": order_id}, timeout=10)


def get_product_image(product_no, product_type="?äººè¥?):
    """?å‚³?†å??–ç?è·¯å?ï¼ˆè‹¥?¾ä??°å??å‚³ Noneï¼‰ã€?""
    try:
        clean_no = str(product_no).upper().strip()
        if not clean_no.startswith("R"):
            clean_no = f"R{clean_no}"
        folder_name = "?äººè¥? if "?äºº" in str(product_type) else "?’ç«¥è¥?
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
#  å°èˆª?‡ç???
# ============================================================
if "page" not in st.session_state:
    st.session_state.page = "?? é¦–é?"
if "cart" not in st.session_state:
    st.session_state.cart = []

cols = st.columns([1.5, 1, 1, 1, 1, 1, 1, 1])
with cols[0]:
    st.markdown(
        "<div style='font-weight:700;font-size:1.1rem;color:#1a1a2e;padding-top:6px;'>"
        "?¢ Gabriel-JL ?²ç«¯</div>",
        unsafe_allow_html=True,
    )

nav_items = [
    ("?? é¦–é?", cols[1]), ("??ï¸??¢å?ä»‹ç´¹", cols[2]),
    ("?? çµ„å?è©¢åƒ¹", cols[3]), ("?? è³¼ç‰©è»?, cols[4]),
    ("?? ç·šä?ä¸‹å–®", cols[5]), ("?’³ ç¶ ç? ECPay", cols[6]),
]
for label, col in nav_items:
    with col:
        if st.button(label, key=f"nav_{label}"):
            st.session_state.page = label
            st.rerun()

page = st.session_state.page

# ---------- é¦–é? ----------
if page == "?? é¦–é?":
    st.markdown(
        "<div class='hero'>"
        "<div class='ducks'><span>??</span><span>??</span><span>??</span></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-title">?±é??¢å?</div>', unsafe_allow_html=True)
    products = api_get_products()
    if products:
        for i in range(0, min(len(products), 20), 4):
            cols4 = st.columns(4)
            for j, p in enumerate(products[i:i + 4]):
                with cols4[j]:
                    img_path = get_product_image(p['product_no'], p['product_type'])
                    if img_path:
                        safe_image(img_path)
                    else:
                        st.info("?“· ?«ç„¡?–ç?")
                    st.markdown(
                        f"<div class='prod-card' style='border-top:none; "
                        f"border-top-left-radius:0; border-top-right-radius:0;'>"
                        f"<h4>{p['product_no']}</h4>"
                        f"<p class='spec'>{p['product_type']} Â· è¦æ ¼ {p['spec']}</p>"
                        f"<p class='price'>NT${p['unit_price']:.0f}<span>/ ?®ä?</span></p>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

# ---------- ?¢å?ä»‹ç´¹ ----------
elif page == "??ï¸??¢å?ä»‹ç´¹":
    st.markdown('<div class="section-title">?¢å?ä»‹ç´¹</div>', unsafe_allow_html=True)
    products = api_get_products()
    if products:
        types = {}
        for p in products:
            types.setdefault(p["product_type"], []).append(p)
        for ptype, items in types.items():
            st.markdown(f"#### {ptype}")
            for i in range(0, len(items), 3):
                cols3 = st.columns(3)
                for j, p in enumerate(items[i:i + 3]):
                    with cols3[j]:
                        img_path = get_product_image(p['product_no'], p['product_type'])
                        if img_path:
                            safe_image(img_path)
                        else:
                            st.info("?“· ?«ç„¡?–ç?")
                        st.markdown(
                            f"<div class='prod-card' style='border-top:none; "
                            f"border-top-left-radius:0; border-top-right-radius:0;'>"
                            f"<h4>{p['product_no']}</h4>"
                            f"<p class='spec'>{p['product_type']} Â· è¦æ ¼ {p['spec']}</p>"
                            f"<p class='price'>NT${p['unit_price']:.0f}<span>/ ?®ä?</span></p>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

# ---------- çµ„å?è©¢åƒ¹ï¼ˆæ??—å·¦?´æ?ç¸®å?ï¼?---------
elif page == "?? çµ„å?è©¢åƒ¹":
    st.markdown('<div class="section-title">çµ„å?è©¢åƒ¹</div>', unsafe_allow_html=True)
    st.caption("é»é¸ ??/ + èª¿æ•´?¸é?ï¼Œç³»çµ±å³?‚è©¦ç®—ç¸½?¹ã€‚åƒ¹?¼æ»¿?å³?¯å??¥è³¼?©è???)
    products = api_get_products()
    if products:
        for p in products:
            key = f"qty_{p['id']}"
            if key not in st.session_state:
                st.session_state[key] = 0

        st.markdown("### ??ï¸??¸æ??¢å??‡æ•¸??)

        # è¡¨é ­
        h1, h2, h3, h4, h5, h6 = st.columns([1, 4, 1, 1, 1, 2])
        with h1:
            st.markdown("**?–ç?**")
        with h2:
            st.markdown("**?¢å?**")
        with h3:
            st.markdown("**??*")
        with h4:
            st.markdown("**?¸é?**")
        with h5:
            st.markdown("**+**")
        with h6:
            st.markdown("**å°è?**")

        st.markdown("---")

        for p in products:
            key = f"qty_{p['id']}"
            qty = st.session_state[key]
            subtotal = p["unit_price"] * qty

            c1, c2, c3, c4, c5, c6 = st.columns([1, 4, 1, 1, 1, 2])

            # ??ç¸®å?
            with c1:
                img_path = get_product_image(p['product_no'], p['product_type'])
                if img_path:
                    safe_image(img_path)
                else:
                    st.markdown(
                        "<div style='width:100%;height:60px;background:#f0f0f0;"
                        "border-radius:8px;display:flex;align-items:center;"
                        "justify-content:center;color:#aaa;font-size:0.75rem;'>"
                        "?¡å?</div>",
                        unsafe_allow_html=True,
                    )

            # ???¢å??ç¨± + ?®åƒ¹
            with c2:
                st.markdown(
                    f"**{p['product_no']} {p['product_type']}**  \n"
                    f"<span style='color:#888;font-size:0.85rem;'>"
                    f"è¦æ ¼ {p['spec']} Â· NT${p['unit_price']:.0f}/?®ä?</span>",
                    unsafe_allow_html=True,
                )

            # ?????‰é?
            with c3:
                if st.button("??, key=f"minus_{p['id']}"):
                    if st.session_state[key] > 0:
                        st.session_state[key] -= 1
                    st.rerun()

            # ???¸é?
            with c4:
                st.markdown(
                    f"<div style='text-align:center;font-weight:700;"
                    f"font-size:1.1rem;padding-top:6px;'>{qty}</div>",
                    unsafe_allow_html=True,
                )

            # ??+ ?‰é?
            with c5:
                if st.button("+", key=f"plus_{p['id']}"):
                    st.session_state[key] += 1
                    st.rerun()

            # ??å°è?
            with c6:
                if qty > 0:
                    st.markdown(
                        f"<div style='color:#e94560;font-weight:800;"
                        f"font-size:1.05rem;padding-top:6px;'>"
                        f"NT${subtotal:,.0f}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='color:#ccc;padding-top:6px;'>??/div>",
                        unsafe_allow_html=True,
                    )

            st.markdown(
                "<hr style='margin:4px 0;border:none;border-top:1px dashed #eee;'>",
                unsafe_allow_html=True,
            )

        # çµ„å?è©¦ç?
        selected = [
            (p, st.session_state[f"qty_{p['id']}"])
            for p in products if st.session_state[f"qty_{p['id']}"] > 0
        ]
        if selected:
            st.markdown("### ?§¾ çµ„å?è©¦ç?")
            total = sum(p["unit_price"] * qty for p, qty in selected)
            for p, qty in selected:
                st.write(
                    f"- {p['product_no']} {p['product_type']} ? {qty} "
                    f"= NT${p['unit_price'] * qty:,.0f}"
                )
            st.markdown(f"**ç¸½è?ï¼šNT${total:,.0f}**")
            if st.button("??? å…¥è³¼ç‰©è»?, type="primary"):
                for p, qty in selected:
                    st.session_state.cart.append({
                        "product_id": p["id"],
                        "name": f"{p['product_no']} {p['product_type']}",
                        "unit_price": p["unit_price"],
                        "qty": qty,
                    })
                    st.session_state[f"qty_{p['id']}"] = 0
                st.success("å·²å??¥è³¼?©è?ï¼?)
                st.rerun()

# ---------- è³¼ç‰©è»?----------
elif page == "?? è³¼ç‰©è»?:
    st.markdown('<div class="section-title">è³¼ç‰©è»?/div>', unsafe_allow_html=True)
    cart = st.session_state.cart
    if not cart:
        st.info("è³¼ç‰©è»Šæ˜¯ç©ºç?ï¼Œè??³ã€Œğ??çµ„å?è©¢åƒ¹?é¸?‡ç”¢?ã€?)
    else:
        total = 0
        for item in cart:
            subtotal = item["unit_price"] * item["qty"]
            total += subtotal
            st.write(f"- **{item['name']}** ? {item['qty']} = NT${subtotal:,.0f}")
        st.markdown(f"### ç¸½è?ï¼šNT${total:,.0f}")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("?¡ï? ?å?çµå¸³ï¼ˆç?ä¸Šä??®ï?", type="primary"):
                st.session_state.page = "?? ç·šä?ä¸‹å–®"
                st.rerun()
        with c2:
            if st.button("??ï¸?æ¸…ç©ºè³¼ç‰©è»?):
                st.session_state.cart = []
                st.rerun()

# ---------- ç·šä?ä¸‹å–® ----------
elif page == "?? ç·šä?ä¸‹å–®":
    st.markdown('<div class="section-title">ç·šä?ä¸‹å–®?‡ä?æ¬?/div>', unsafe_allow_html=True)
    cart = st.session_state.cart
    if not cart:
        st.warning("è³¼ç‰©è»Šæ˜¯ç©ºç??‚è??ˆè‡³?Œğ??çµ„å?è©¢åƒ¹?é¸?‡ç”¢?ã€?)
    else:
        total = sum(item["unit_price"] * item["qty"] for item in cart)
        st.markdown(f"### ?? è¨‚å–®ç¸½è?ï¼šNT${total:,.0f}")

        with st.form("checkout_form"):
            customer_name = st.text_input("?¯çµ¡äººå???*")
            customer_email = st.text_input("Email *")
            customer_phone = st.text_input("?»è©±")
            note = st.text_area("?™è¨»")
            submitted = st.form_submit_button("ç¢ºè?å»ºç?è¨‚å–®")

        if submitted:
            if not customer_name or not customer_email:
                st.error("è«‹å¡«å¯«å??è? Email")
            else:
                payload = {
                    "customer_name": customer_name,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "order_date": date.today().isoformat(),
                    "delivery_date": (date.today() + timedelta(days=1)).isoformat(),
                    "total_amount": total,
                    "note": note,
                    "items": [
                        {
                            "product_id": i["product_id"],
                            "unit_price": i["unit_price"],
                            "qty": i["qty"],
                        }
                        for i in cart
                    ],
                }

                try:
                    r = requests.post(f"{API_BASE}/api/orders", json=payload, timeout=8)
                    if r.status_code == 201:
                        res = r.json()
                        o = res.get("order", {})
                        st.success(f"??è¨‚å–® #{o.get('id')} å»ºç??å?ï¼?)
                        st.session_state.cart = []

                        ok_pay, pay_res = api_ecpay_create_order(o.get('id'))
                        if ok_pay and "redirect_url" in pay_res:
                            pay_url = f"{API_BASE}{pay_res['redirect_url']}"
                            st.markdown(
                                f'<a href="{pay_url}" target="_blank" '
                                f'style="display:inline-block;padding:12px 24px;'
                                f'background:#635BFF;color:#fff;border-radius:8px;'
                                f'text-decoration:none;font-weight:bold;margin-top:10px;">'
                                f'?? é»æ­¤?å?ç¶ ç?ä»˜æ¬¾?é¢</a>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.info("è¨‚å–®å·²æ?ç«‹ï??¨å¯ä»¥è‡³?Œğ??ç¶ ç? ECPay?é??¢å??ä?æ¬¾ã€?)
                    else:
                        st.error(f"å»ºç?å¤±æ?ï¼š{r.text}")
                except Exception as e:
                    st.error(f"????¯èª¤ï¼š{str(e)}")

# ---------- ç¶ ç? ECPay ----------
elif page == "?’³ ç¶ ç? ECPay":
    st.markdown(
        '<div class="section-title">ç¶ ç? ECPay å¿«é€Ÿä?æ¬¾è?è¨­å?</div>',
        unsafe_allow_html=True,
    )
    cfg = api_ecpay_config()
    if cfg.get("configured"):
        st.success("??ç¶ ç? ECPay ç³»çµ±å·²è¨­å®šå???)
    else:
        st.warning("? ï? ç¶ ç? ECPay ?®å??ºæœªè¨­å??–æ¸¬è©¦ç??‹ã€?)

    st.markdown("### ?’³ å¾…ä?æ¬¾è??®å?è¡?)
    orders = api_get_orders()
    pending = [o for o in orders if o.get("payment_status") == "pending"]
    if not pending:
        st.info("?®å?æ²’æ?å¾…ä?æ¬¾ç?è¨‚å–®??)
    else:
        for o in pending:
            with st.expander(
                f"è¨‚å–® #{o['id']} Â· {o['customer_name']} Â· NT${o['total_amount']:,.0f}"
            ):
                st.write("**è¨‚å–®?ç´°ï¼?*")
                for item in o.get("items", []):
                    st.write(
                        f"- {item['product_no']} {item['product_type']} ? "
                        f"{item['quantity']} (?®åƒ¹ NT${item['unit_price']})"
                    )
                if st.button(f"?’³ ?¢ç?ç¶ ç?ä»˜æ¬¾??? #{o['id']}", key=f"pay_btn_{o['id']}"):
                    ok, res = api_ecpay_create_order(o["id"])
                    if ok and "redirect_url" in res:
                        pay_url = f"{API_BASE}{res['redirect_url']}"
                        st.markdown(
                            f'<a href="{pay_url}" target="_blank" '
                            f'style="display:inline-block;padding:12px 24px;'
                            f'background:#635BFF;color:#fff;border-radius:8px;'
                            f'text-decoration:none;font-weight:bold;margin-top:8px;">'
                            f'?? é»æ­¤?å?ç¶ ç?ä»˜æ¬¾?é¢</a>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error("?¡æ??¢ç?ä»˜æ¬¾???ï¼Œè?æª¢æŸ¥å¾Œç«¯ç¶ ç??ƒæ•¸??)
