import os
import requests
import urllib3
from django.conf import settings

# Disable SSL warnings — Windows SSL certificate fix
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NETWORK_CODE_MAP = {
    '62120': 'Airtel Nigeria',
    '62130': 'MTN Nigeria',
    '62150': 'Glo Nigeria',
    '62160': '9mobile Nigeria',
}

INCIDENT_TYPE_MAP = {
    'DV': 'Domestic Violence',
    'SA': 'Sexual Assault',
    'H':  'Harassment',
    'CA': 'Child Abuse',
}

SEVERITY_MAP = {
    'LOW':  'Low',
    'MED':  'Medium',
    'HIGH': 'High',
    'CRIT': 'Critical',
}

VALID_CITIES = [
    'Abuja', 'Enugu', 'Kaduna', 'Kafanchan',
    'Kano', 'Lagos', 'Port Harcourt',
    'Ibadan', 'Uyo', 'Zaria'
]

# Africa's Talking API URLs
AT_SMS_URL = 'https://api.sandbox.africastalking.com/version1/messaging'

def normalise_phone(number: str) -> str:
    """
    Converts Nigerian local format to international format.
    09022355689   → +2349022355689
    08045232565   → +2348045232565
    2349022355689 → +2349022355689
    +2349022355689 → +2349022355689 (unchanged)
    """
    number = number.strip().replace(' ', '').replace('-', '')

    if number.startswith('+234'):
        return number

    if number.startswith('234') and len(number) == 13:
        return f'+{number}'

    if number.startswith('0') and len(number) == 11:
        return f'+234{number[1:]}'

    return number

def send_sms(to_number, message):
    """
    Sends SMS via Africa's Talking REST API directly.
    No SDK — avoids SSL certificate issues on Windows.
    verify=False bypasses SSL verification for development.
    """
    to_number = normalise_phone(to_number)  # ← add this line
    
    headers = {
        'apiKey': settings.AT_API_KEY,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
    }
    payload = {
        'username': settings.AT_USERNAME,
        'to': to_number,
        'message': message,
    }
    try:
        response = requests.post(
            AT_SMS_URL,
            headers=headers,
            data=payload,
            verify=False,      # bypasses SSL — safe for development
            timeout=10,
        )
        print(f'[AT SMS] Sent to {to_number} — Status: {response.status_code}')
        print(f'[AT SMS] Response: {response.text}')
        return True
    except requests.exceptions.Timeout:
        print(f'[AT SMS Error] Timeout sending to {to_number}')
        return False
    except requests.exceptions.ConnectionError as e:
        print(f'[AT SMS Error] Connection failed to {to_number}: {e}')
        return False
    except Exception as e:
        print(f'[AT SMS Error] Unexpected error sending to {to_number}: {e}')
        return False


def carrier_from_code(code):
    return NETWORK_CODE_MAP.get(str(code), 'Unknown')


def normalise_city(city_text):
    for city in VALID_CITIES:
        if city.lower() == city_text.lower():
            return city
    for city in VALID_CITIES:
        if city_text.lower() in city.lower():
            return city
    return city_text.capitalize()