import json
try:
    with open('processing_msg_prefs.json') as f:
        print(json.load(f))
except Exception as e:
    print(e)
try:
    with open('tools/order_tracking/config.json') as f:
        print(json.load(f).get('processing_messages'))
except Exception as e:
    print(e)
