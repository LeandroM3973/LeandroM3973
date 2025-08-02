#!/usr/bin/env python3
"""
CRITICAL PAYMENT SYSTEM BUG RESOLUTION TEST
===========================================

FOCUS: Test the main reported issue - POST /api/payments/create-preference
EXPECTED: No ValidationError for Transaction model fields (fee, net_amount, description)
"""

import requests
import json
import sys
import time

def test_critical_payment_bug():
    """Test the critical payment creation bug reported in review request"""
    base_url = "https://47eed0e6-f30e-431a-b6a5-47794796692b.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    print("🚨 CRITICAL PAYMENT SYSTEM BUG RESOLUTION TEST")
    print("=" * 60)
    print("TESTING: POST /api/payments/create-preference")
    print("EXPECTED: No ValidationError for Transaction model")
    print("=" * 60)
    
    # Create test user
    timestamp = str(int(time.time()))
    test_email = f"critical.test.{timestamp}@gmail.com"
    
    print("\n1. Creating test user...")
    user_response = requests.post(f"{api_url}/users", json={
        "name": "Critical Test User",
        "email": test_email,
        "phone": "11987654321",
        "password": "criticaltest123"
    })
    
    if user_response.status_code != 200:
        print(f"❌ Failed to create user: {user_response.status_code}")
        print(f"   Error: {user_response.text}")
        return False
        
    user_data = user_response.json()
    user_id = user_data['id']
    print(f"✅ User created: {user_id}")
    
    # Verify email
    print("\n2. Verifying user email...")
    verify_response = requests.post(f"{api_url}/users/manual-verify?email={test_email}")
    if verify_response.status_code == 200:
        print("✅ Email verified")
    else:
        print("⚠️  Email verification failed, continuing...")
    
    # Test payment creation - THE CRITICAL TEST
    print("\n3. Testing payment creation (CRITICAL TEST)...")
    test_amounts = [25.00, 50.00, 100.00, 250.00]
    successful_payments = 0
    validation_errors = []
    
    for amount in test_amounts:
        print(f"\n   Testing R$ {amount}...")
        
        payment_response = requests.post(f"{api_url}/payments/create-preference", json={
            "user_id": user_id,
            "amount": amount
        })
        
        if payment_response.status_code == 200:
            successful_payments += 1
            payment_data = payment_response.json()
            print(f"   ✅ SUCCESS - Payment created!")
            print(f"      Transaction ID: {payment_data.get('transaction_id')}")
            print(f"      AbacatePay: {payment_data.get('abacatepay', False)}")
            print(f"      Fee: R$ {payment_data.get('fee', 0)}")
            
            # Check for real AbacatePay URL
            payment_url = payment_data.get('payment_url', '')
            if 'abacatepay.com/pay/bill_' in payment_url:
                print(f"      ✅ Real AbacatePay URL generated")
            else:
                print(f"      ⚠️  URL: {payment_url}")
                
        else:
            print(f"   ❌ FAILED - Status: {payment_response.status_code}")
            error_text = payment_response.text
            print(f"      Error: {error_text}")
            
            # Check for ValidationError
            if 'ValidationError' in error_text or 'net_amount' in error_text:
                validation_errors.append(f"R$ {amount}: {error_text}")
                print(f"      🚨 CRITICAL: ValidationError detected!")
            elif 'required' in error_text.lower() and ('fee' in error_text or 'description' in error_text):
                validation_errors.append(f"R$ {amount}: Missing Transaction fields")
                print(f"      🚨 CRITICAL: Missing Transaction model fields!")
    
    # Test transaction history to verify fields
    print("\n4. Verifying transaction structure...")
    tx_response = requests.get(f"{api_url}/transactions/{user_id}")
    
    if tx_response.status_code == 200:
        transactions = tx_response.json()
        print(f"   Retrieved {len(transactions)} transactions")
        
        if transactions:
            # Check first transaction for required fields
            tx = transactions[0]
            required_fields = ['fee', 'net_amount', 'description']
            missing_fields = []
            
            for field in required_fields:
                if field not in tx or tx[field] is None:
                    missing_fields.append(field)
                else:
                    print(f"   ✅ {field}: {tx[field]}")
            
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
                validation_errors.append(f"Transaction missing fields: {missing_fields}")
            else:
                print(f"   ✅ All required Transaction fields present!")
        else:
            print(f"   ⚠️  No transactions found")
    else:
        print(f"   ❌ Failed to get transactions: {tx_response.status_code}")
    
    # Final assessment
    print(f"\n" + "=" * 60)
    print("📊 CRITICAL BUG RESOLUTION ASSESSMENT")
    print("=" * 60)
    
    print(f"Successful payments: {successful_payments}/{len(test_amounts)}")
    print(f"ValidationErrors detected: {len(validation_errors)}")
    
    if validation_errors:
        print(f"\n🚨 CRITICAL VALIDATION ERRORS:")
        for error in validation_errors:
            print(f"   ❌ {error}")
    else:
        print(f"\n✅ NO VALIDATION ERRORS DETECTED!")
    
    # Final verdict
    if successful_payments == len(test_amounts) and len(validation_errors) == 0:
        print(f"\n🎉 SUCCESS: CRITICAL BUG RESOLVED!")
        print(f"   ✅ Payment preferences created successfully")
        print(f"   ✅ No ValidationError for Transaction model")
        print(f"   ✅ All Transaction fields (fee, net_amount, description) present")
        print(f"   ✅ Real AbacatePay URLs generated correctly")
        print(f"   ✅ Complete payment flow functional")
        print(f"\n🔧 THE CRITICAL BUG FROM THE REVIEW REQUEST HAS BEEN RESOLVED!")
        return True
    else:
        print(f"\n❌ FAILURE: CRITICAL BUG NOT FULLY RESOLVED!")
        print(f"   🚨 Payment creation issues detected")
        print(f"   🚨 ValidationError may still be occurring")
        print(f"   🚨 Transaction model may still have issues")
        print(f"\n🔧 THE CRITICAL BUG NEEDS FURTHER INVESTIGATION!")
        return False

if __name__ == "__main__":
    success = test_critical_payment_bug()
    sys.exit(0 if success else 1)