import os
import mercadopago
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

print("🔍 Mercado Pago Configuration Test")
print("=" * 50)

# Get the access token
mp_access_token = os.environ.get('MERCADO_PAGO_ACCESS_TOKEN')
print(f"Access Token: {mp_access_token}")
print(f"Token Length: {len(mp_access_token) if mp_access_token else 0}")

if mp_access_token:
    print(f"Token starts with: {mp_access_token[:10]}...")
    
    # Check if it looks like a valid MP token
    if mp_access_token.startswith('APP_USR-') or mp_access_token.startswith('TEST-'):
        print("✅ Token format looks correct")
    else:
        print("❌ Token format looks incorrect")
        print("   Valid MP tokens start with 'APP_USR-' (production) or 'TEST-' (sandbox)")
    
    # Try to initialize SDK
    try:
        mp = mercadopago.SDK(mp_access_token)
        print("✅ Mercado Pago SDK initialized successfully")
        
        # Try to create a simple test preference
        test_preference = {
            "items": [
                {
                    "title": "Test Item",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "currency_id": "BRL"
                }
            ],
            "payer": {
                "name": "Test User",
                "email": "test@example.com"
            }
        }
        
        print("\n🧪 Testing preference creation...")
        response = mp.preference().create(test_preference)
        print(f"Response status: {response.get('status')}")
        print(f"Response: {response}")
        
        if response.get('status') == 201:
            print("✅ Test preference created successfully!")
        else:
            print("❌ Failed to create test preference")
            
    except Exception as e:
        print(f"❌ Error with Mercado Pago SDK: {str(e)}")
else:
    print("❌ No access token found in environment variables")

print("\n🔍 Environment Variables Check:")
print(f"MERCADO_PAGO_ACCESS_TOKEN: {'SET' if mp_access_token else 'NOT SET'}")
print(f"MERCADO_PAGO_PUBLIC_KEY: {'SET' if os.environ.get('MERCADO_PAGO_PUBLIC_KEY') else 'NOT SET'}")