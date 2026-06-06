# raw_test.py
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = 'https://api.sandbox.africastalking.com/version1/messaging'
headers = {
    'apiKey': 'atsk_a29fe7557d13cff112e29159ce188843f17f60d72e6b06a08dd8b371b451046828eaaeac',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'application/json',
}
payload = {
    'username': 'sandbox',
    'to': '+2349055940025',
    'message': 'SafePulse test message',
}

try:
    response = requests.post(url, headers=headers, data=payload, verify=False, timeout=10)
    print("STATUS:", response.status_code)
    print("RESPONSE:", response.text)
except Exception as e:
    print("ERROR:", e)
