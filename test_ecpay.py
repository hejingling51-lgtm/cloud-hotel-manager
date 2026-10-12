import hashlib
import urllib.parse
import re


def ecpay_url_encode(s):
    encoded = urllib.parse.quote(s, safe='-_.!*()')
    return re.sub(r'%[0-9A-Fa-f]{2}',
                  lambda m: m.group(0).lower(), encoded)


# 绿界官方测试案例
params = {
    'MerchantID': '3002607',
    'MerchantTradeNo': 'Test1234567890',
    'MerchantTradeDate': '2023/01/01 12:00:00',
    'PaymentType': 'aio',
    'TotalAmount': '100',
    'TradeDesc': 'Test',
    'ItemName': 'Test',
    'ReturnURL': 'https://example.com',
    'ChoosePayment': 'ALL',
    'EncryptType': '1',
}
HashKey = 'pwFHCqoQZGmho4w6'
HashIV = 'EkRm7iFT261dpevs'

sorted_items = sorted(params.items(), key=lambda x: x[0].lower())
qs = '&'.join(f'{k}={v}' for k, v in sorted_items)
raw = f'HashKey={HashKey}&{qs}&HashIV={HashIV}'
encoded = ecpay_url_encode(raw)
result = hashlib.sha256(encoded.encode('utf-8')).hexdigest().upper()

print('=' * 60)
print('[1] 拼接字串 (raw)：')
print(raw)
print()
print('[2] URL encode 后：')
print(encoded)
print()
print('[3] CheckMacValue：')
print(result)
print('=' * 60)