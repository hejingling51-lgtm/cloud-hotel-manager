@echo off
cd /d C:\Users\user\cloudhotel
set ECPAY_MERCHANT_ID=3002607
set ECPAY_HASH_KEY=pwFHCqoQZGmho4w6
set ECPAY_HASH_IV=EkRm7iFT261dpevs
set ECPAY_API_URL=https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5
set ECPAY_RETURN_URL=https://example.com/api/ecpay/notify
set ECPAY_CLIENT_BACK_URL=https://example.com
set ECPAY_DEBUG=1
python app.py