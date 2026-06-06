# test_at.py

import africastalking

africastalking.initialize(
    username="sandbox",
    api_key="atsk_a29fe7557d13cff112e29159ce188843f17f60d72e6b06a08dd8b371b451046828eaaeac"
)

sms = africastalking.SMS

response = sms.send(
    "Hello from SafePulse",
    ["+2349055940025"]
)

print(response)