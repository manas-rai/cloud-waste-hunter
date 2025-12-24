#!/usr/bin/env python3
"""
Quick test for batch approve API
"""
import requests
import json

# Test payload
payload = {
    "detection_ids": [13, 17, 16],
    "approved_by": "user@example.com",
    "dry_run": False
}

print("Testing batch approve API...")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(
        "http://localhost:8000/api/v1/actions/batch/approve",
        json=payload
    )
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ SUCCESS!")
    else:
        print(f"\n❌ FAILED with status {response.status_code}")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")

