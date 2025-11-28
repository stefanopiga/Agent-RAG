import sys
import time

import requests

BASE_URL = "http://localhost:8000"


def test_health():
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("[OK] /health check passed")
            print(response.json())
            return True
        else:
            print(f"[FAIL] /health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] /health check failed: {e}")
        return False


def test_search():
    print("\nTesting /v1/search endpoint...")
    payload = {"query": "test query", "limit": 2}
    try:
        response = requests.post(f"{BASE_URL}/v1/search", json=payload)
        if response.status_code == 200:
            data = response.json()
            print("[OK] /v1/search check passed")
            print(f"Found {data.get('count')} results")
            return True
        else:
            print(f"[FAIL] /v1/search check failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"[FAIL] /v1/search check failed: {e}")
        return False


def main():
    # Wait for server to start
    print("Waiting for server to start...")
    for i in range(10):
        if test_health():
            break
        time.sleep(2)
    else:
        print("Server failed to start in time.")
        sys.exit(1)

    # Run search test
    if not test_search():
        print("Search test failed.")
        sys.exit(1)

    print("\nAll verification tests passed! 🚀")


if __name__ == "__main__":
    main()
