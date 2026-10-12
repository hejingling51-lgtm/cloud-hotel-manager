powershell
Set-Location C:\Users\user\cloudhotel
$env:ECPAY_MERCHANT_ID   = "3002607"
$env:ECPAY_HASH_KEY      = "pwFHCqoQZGmho4w6"
$env:ECPAY_HASH_IV       = "EkRm7iFT261dpevs"
$env:ECPAY_API_URL       = "https://payment-stage.ecpay.com.tw/Cashier/AioCheckOut/V5"
$env:ECPAY_RETURN_URL    = "https://example.com/api/ecpay/notify"
$env:ECPAY_CLIENT_BACK_URL = "https://example.com"
$env:ECPAY_DEBUG         = "1"
python app.py