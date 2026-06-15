from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
})

API_KEY = os.environ.get('API_KEY', 'changeme123')

def check_key():
    return request.headers.get('X-API-Key') == API_KEY

@app.route('/')
def index():
    return jsonify({'status': 'ok', 'message': 'Price Proxy is running!'})

@app.route('/login', methods=['POST'])
def login():
    if not check_key():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.json
    login_url    = data.get('login_url')
    username     = data.get('username')
    password     = data.get('password')
    u_field      = data.get('username_field', 'Input.Email')
    p_field      = data.get('password_field', 'Input.Password')

    try:
        # دریافت توکن CSRF
        r = SESSION.get(login_url, timeout=15, verify=False)
        rvt = ''
        soup = BeautifulSoup(r.text, 'html.parser')
        token_input = soup.find('input', {'name': '__RequestVerificationToken'})
        if token_input:
            rvt = token_input.get('value', '')

        # ارسال فرم لاگین
        post_data = {
            u_field: username,
            p_field: password,
            '__RequestVerificationToken': rvt
        }
        r2 = SESSION.post(login_url, data=post_data, timeout=15, verify=False, allow_redirects=True)

        if r2.status_code == 200 and 'Logout' in r2.text:
            return jsonify({'success': True})
        elif r2.history and r2.history[-1].status_code == 302:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': f'لاگین ناموفق. کد HTTP: {r2.status_code}'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/fetch-price', methods=['POST'])
def fetch_price():
    if not check_key():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data     = request.json
    url      = data.get('url')
    selector = data.get('selector')

    if not url or not selector:
        return jsonify({'success': False, 'error': 'url و selector الزامی هستند.'})

    try:
        r = SESSION.get(url, timeout=15, verify=False)

        if r.status_code != 200:
            return jsonify({'success': False, 'error': f'کد HTTP: {r.status_code}'})

        html = r.text

        # بررسی موجودی
        if 'موجود نمی باشد' in html:
            return jsonify({'success': True, 'available': False, 'price': None})

        # استخراج قیمت با BeautifulSoup + XPath شبیه‌سازی
        from lxml import etree
        import re
        tree = etree.HTML(html)
        elements = tree.xpath(selector)

        if not elements:
            snippet = BeautifulSoup(html, 'html.parser').get_text()[:300]
            return jsonify({'success': False, 'error': 'سلکتور نتیجه‌ای نداشت.', 'html_snippet': snippet})

        raw = elements[0].text_content() if hasattr(elements[0], 'text_content') else str(elements[0])
        price_rial = re.sub(r'[^0-9]', '', raw)

        if not price_rial or int(price_rial) <= 0:
            return jsonify({'success': False, 'error': f'عدد معتبری استخراج نشد. متن خام: {raw}'})

        return jsonify({'success': True, 'available': True, 'price_rial': int(price_rial), 'raw': raw})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
