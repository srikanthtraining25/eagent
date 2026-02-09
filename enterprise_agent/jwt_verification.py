import sys
import os
import jwt
import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from enterprise_agent.app.services.middleware import validate_token
from enterprise_agent.app.core.config import settings

def test_jwt_validation():
    print("--- Testing JWT Validation ---")
    
    secret = settings.JWT_SECRET_KEY
    algo = settings.JWT_ALGORITHM
    
    # 1. Generate Valid Token
    payload = {
        "id": "jwt_user_1",
        "role": "admin",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    valid_token = jwt.encode(payload, secret, algorithm=algo)
    print(f"Generated Token: {valid_token[:20]}...")
    
    decoded = validate_token(valid_token)
    if decoded and decoded["id"] == "jwt_user_1":
        print("[PASS] Valid token decoded successfully.")
    else:
        print(f"[FAIL] Valid token failed: {decoded}")

    # 2. Test Expired Token
    expired_payload = {
        "id": "expired_user",
        "exp": datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    }
    expired_token = jwt.encode(expired_payload, secret, algorithm=algo)
    
    decoded_expired = validate_token(expired_token)
    if decoded_expired is None:
        print("[PASS] Expired token correctly rejected.")
    else:
        print("[FAIL] Expired token was accepted!")

    # 3. Test Invalid Signature
    fake_token = jwt.encode(payload, "wrong_secret", algorithm=algo)
    decoded_fake = validate_token(fake_token)
    if decoded_fake is None:
        print("[PASS] Invalid signature correctly rejected.")
    else:
        print("[FAIL] Invalid signature was accepted!")

if __name__ == "__main__":
    test_jwt_validation()
