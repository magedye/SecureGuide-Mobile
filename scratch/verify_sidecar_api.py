import urllib.request
import urllib.error
import json
import uuid

BASE_URL = "http://127.0.0.1:8765"

def req(path, method="POST", data=None, headers=None):
    if headers is None: headers = {}
    if data:
        data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read().decode("utf-8"), dict(response.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), dict(e.headers)
    except Exception as e:
        return 0, str(e), {}

def test_cors():
    print("--- CORS Tests ---")
    
    print("1. GET without Origin -> works")
    s, b, h = req("/health", method="GET")
    print(f"Status: {s}, CORS Header: {h.get('Access-Control-Allow-Origin')}")
    
    print("2. GET with untrusted Origin -> No CORS")
    s, b, h = req("/health", method="GET", headers={"Origin": "http://evil.com"})
    print(f"Status: {s}, CORS Header: {h.get('Access-Control-Allow-Origin')}")

    print("3. OPTIONS with untrusted Origin -> No wildcard")
    s, b, h = req("/write/assessments", method="OPTIONS", headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "POST"})
    print(f"Status: {s}, CORS Header: {h.get('Access-Control-Allow-Origin')}")

    print("4. POST with untrusted Origin -> No CORS")
    s, b, h = req("/write/assessments", method="POST", data={"artifactId": "ART-001"}, headers={"Origin": "http://evil.com"})
    print(f"Status: {s}, CORS Header: {h.get('Access-Control-Allow-Origin')}")


def test_score():
    print("\n--- Score Validation Tests ---")
    
    base_data = {"artifactId": "ART-XXX", "assessorName": "Tester"}
    
    test_cases = [
        ("invalid", 400),
        ("NaN", 400),
        ("Infinity", 400),
        ("-Infinity", 400),
        ("-1", 400),
        ("101", 400),
        ("50", 404) # 404 because ART-XXX is not found, but it passed validation!
    ]
    
    for val, expected_status in test_cases:
        data = base_data.copy()
        data["score"] = val
        s, b, h = req("/write/assessments", method="POST", data=data)
        print(f"Score {val} -> Status: {s} (Expected: {expected_status})")

def test_endpoints():
    print("\n--- Write Endpoints Tests ---")
    
    print("1. /write/templates/apply - Missing Fields")
    s, b, h = req("/write/templates/apply", data={})
    print(f"Status: {s}, Response: {b}")

    print("2. /write/evidence - Missing Fields")
    s, b, h = req("/write/evidence", data={"artifactId": "ART-123"})
    print(f"Status: {s}, Response: {b}")

    print("3. /write/exceptions - Non-existent Entity")
    s, b, h = req("/write/exceptions", data={
        "artifactId": "ART-NONEXISTENT", 
        "exceptionStatus": "EXC-APPROVED", 
        "justification": "test"
    })
    print(f"Status: {s}, Response: {b}")

if __name__ == "__main__":
    test_cors()
    test_score()
    test_endpoints()
