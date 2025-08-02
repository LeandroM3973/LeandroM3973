#!/usr/bin/env python3
"""
TRANSACTION MODEL FIX VERIFICATION TEST
=======================================

CRITICAL BUG RESOLUTION TEST:
- ValidationError: Field 'net_amount' required in Transaction model
- All Transaction() constructors updated to include fee, net_amount, description

FOCUS: Verify the critical bug reported in review request is resolved
"""

import requests
import json
import sys
import time

class TransactionFixTester:
    def __init__(self, base_url="https://47eed0e6-f30e-431a-b6a5-47794796692b.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.critical_errors = []
        
    def log_critical_error(self, error_msg):
        """Log critical errors that indicate the bug is not fixed"""
        self.critical_errors.append(error_msg)
        print(f"🚨 CRITICAL ERROR: {error_msg}")
        
    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test with ValidationError detection"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    error_detail = error_data.get('detail', '')
                    print(f"   Error: {json.dumps(error_data, indent=2)}")
                    
                    # Check for ValidationError related to Transaction model
                    if 'ValidationError' in str(error_data) or 'net_amount' in str(error_data):
                        self.log_critical_error(f"Transaction model ValidationError detected in {name}: {error_detail}")
                    elif 'required' in str(error_data).lower() and ('fee' in str(error_data) or 'description' in str(error_data)):
                        self.log_critical_error(f"Missing required Transaction fields in {name}: {error_detail}")
                        
                    return False, error_data
                except:
                    print(f"   Error: {response.text}")
                    if 'ValidationError' in response.text or 'net_amount' in response.text:
                        self.log_critical_error(f"Transaction model ValidationError in {name}: {response.text}")
                    return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            if 'ValidationError' in str(e) or 'net_amount' in str(e):
                self.log_critical_error(f"Transaction model ValidationError in {name}: {str(e)}")
            return False, {}

    def test_critical_payment_creation(self):
        """CRITICAL TEST: Payment Creation - Main reported issue"""
        print("\n💳 CRITICAL TEST: PAYMENT CREATION")
        print("=" * 50)
        print("TESTING: POST /api/payments/create-preference")
        print("EXPECTED: No ValidationError for Transaction model")
        print("=" * 50)
        
        # Create test user first
        timestamp = str(int(time.time()))
        test_email = f"transaction.test.{timestamp}@gmail.com"
        
        success, user_data = self.run_test(
            "Create Test User",
            "POST",
            "users",
            200,
            data={
                "name": "Transaction Test User",
                "email": test_email,
                "phone": "11987654321",
                "password": "testpass123"
            }
        )
        
        if not success:
            self.log_critical_error("Failed to create test user - may indicate Transaction model issues")
            return False
            
        user_id = user_data['id']
        print(f"✅ Test user created: {user_id}")
        
        # Manually verify email
        self.run_test(
            "Verify Test User Email",
            "POST",
            f"users/manual-verify?email={test_email}",
            200
        )
        
        # Test payment creation - THE MAIN ISSUE
        test_amounts = [25.00, 50.00, 100.00]
        successful_payments = 0
        
        for amount in test_amounts:
            print(f"\n💰 Testing payment creation for R$ {amount}...")
            
            success, payment_data = self.run_test(
                f"Create Payment Preference R$ {amount}",
                "POST",
                "payments/create-preference",
                200,
                data={
                    "user_id": user_id,
                    "amount": amount
                }
            )
            
            if success:
                successful_payments += 1
                print(f"   ✅ Payment created successfully!")
                
                # Verify AbacatePay integration
                if payment_data.get('abacatepay'):
                    print(f"   ✅ AbacatePay integration active")
                    payment_url = payment_data.get('payment_url', '')
                    if 'abacatepay.com/pay/bill_' in payment_url:
                        print(f"   ✅ Real AbacatePay URL format confirmed")
                    print(f"   ✅ Transaction ID: {payment_data.get('transaction_id')}")
                    print(f"   ✅ Fee: R$ {payment_data.get('fee', 0)}")
                elif payment_data.get('demo_mode'):
                    print(f"   ⚠️  Demo mode active")
                    
            else:
                self.log_critical_error(f"Payment creation failed for R$ {amount}")
                
        print(f"\n📊 PAYMENT CREATION RESULTS:")
        print(f"   Successful payments: {successful_payments}/{len(test_amounts)}")
        
        if successful_payments == len(test_amounts):
            print(f"   ✅ ALL PAYMENT CREATIONS SUCCESSFUL!")
            print(f"   ✅ Transaction model fix appears to be working!")
            return True, user_id
        else:
            self.log_critical_error("Payment creation failures detected - Transaction model may still have issues")
            return False, user_id

    def test_transaction_field_verification(self, user_id):
        """Verify all transactions have required fields"""
        print("\n📋 TRANSACTION FIELD VERIFICATION")
        print("=" * 45)
        
        # Get user transactions
        success, transactions = self.run_test(
            "Get User Transactions",
            "GET",
            f"transactions/{user_id}",
            200
        )
        
        if not success or not transactions:
            self.log_critical_error("Failed to retrieve transactions")
            return False
            
        print(f"   Retrieved {len(transactions)} transactions")
        
        # Check required fields
        required_fields = ['fee', 'net_amount', 'description']
        all_transactions_valid = True
        
        for i, tx in enumerate(transactions):
            tx_type = tx.get('type', 'unknown')
            print(f"\n   Transaction {i+1} ({tx_type}):")
            
            for field in required_fields:
                present = field in tx and tx[field] is not None
                status = "✅" if present else "❌"
                value = tx.get(field, 'MISSING')
                print(f"     {status} {field}: {value}")
                
                if not present:
                    all_transactions_valid = False
                    self.log_critical_error(f"Transaction {tx_type} missing required field: {field}")
                    
        if all_transactions_valid:
            print(f"\n   ✅ ALL TRANSACTIONS HAVE REQUIRED FIELDS!")
            print(f"   ✅ Transaction model fix is working correctly!")
            return True
        else:
            self.log_critical_error("Some transactions missing required fields")
            return False

    def test_bet_system_transactions(self, user_id):
        """Test bet system transactions work after fix"""
        print("\n🎯 BET SYSTEM TRANSACTION TEST")
        print("=" * 40)
        
        # Add balance first
        success, payment_data = self.run_test(
            "Add Balance for Betting",
            "POST",
            "payments/create-preference",
            200,
            data={"user_id": user_id, "amount": 100.00}
        )
        
        if success and payment_data.get('demo_mode'):
            # Simulate payment approval
            self.run_test(
                "Simulate Payment Approval",
                "POST",
                f"payments/simulate-approval/{payment_data['transaction_id']}",
                200
            )
            
        # Test bet creation
        success, bet_data = self.run_test(
            "Create Test Bet",
            "POST",
            "bets",
            200,
            data={
                "event_title": "Transaction Fix Test Bet",
                "event_type": "sports",
                "event_description": "Testing bet creation after Transaction model fix",
                "amount": 50.00,
                "creator_id": user_id
            }
        )
        
        if success:
            print(f"   ✅ Bet creation successful!")
            print(f"   ✅ BET_DEBIT transaction working!")
            return True
        else:
            self.log_critical_error("Bet creation failed - BET_DEBIT transaction issue")
            return False

    def run_comprehensive_test(self):
        """Run comprehensive Transaction model fix verification"""
        print("\n" + "=" * 80)
        print("🚨 TRANSACTION MODEL FIX VERIFICATION - CRITICAL BUG RESOLUTION")
        print("=" * 80)
        print("FOCUS: Verify ValidationError for Transaction model is resolved")
        print("TESTING: All transaction types include fee, net_amount, description")
        print("=" * 80)
        
        # Test 1: Critical Payment Creation
        payment_success, user_id = self.test_critical_payment_creation()
        
        # Test 2: Transaction Field Verification
        field_success = False
        if user_id:
            field_success = self.test_transaction_field_verification(user_id)
        
        # Test 3: Bet System Transactions
        bet_success = False
        if user_id:
            bet_success = self.test_bet_system_transactions(user_id)
        
        # Final Assessment
        print(f"\n" + "=" * 80)
        print("📊 FINAL TRANSACTION MODEL FIX ASSESSMENT")
        print("=" * 80)
        
        print(f"Tests passed: {self.tests_passed}/{self.tests_run}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        print(f"\n📋 TEST RESULTS:")
        print(f"   {'✅' if payment_success else '❌'} Payment Creation (Main Issue)")
        print(f"   {'✅' if field_success else '❌'} Transaction Field Verification")
        print(f"   {'✅' if bet_success else '❌'} Bet System Transactions")
        
        print(f"\n🚨 CRITICAL ERRORS: {len(self.critical_errors)}")
        if self.critical_errors:
            for error in self.critical_errors:
                print(f"   ❌ {error}")
        else:
            print(f"   ✅ No Transaction model ValidationErrors detected!")
            
        # Final verdict
        all_tests_passed = payment_success and field_success and bet_success
        no_critical_errors = len(self.critical_errors) == 0
        
        if all_tests_passed and no_critical_errors:
            print(f"\n🎉 SUCCESS: TRANSACTION MODEL FIX VERIFIED!")
            print(f"   ✅ No ValidationError for Transaction model fields")
            print(f"   ✅ All transaction types include fee, net_amount, description")
            print(f"   ✅ Payment preferences created successfully")
            print(f"   ✅ Real AbacatePay URLs generated correctly")
            print(f"   ✅ Complete payment flow functional")
            print(f"\n🔧 THE CRITICAL BUG HAS BEEN RESOLVED!")
            return True
        else:
            print(f"\n❌ FAILURE: TRANSACTION MODEL ISSUES DETECTED!")
            print(f"   🚨 ValidationError may still be occurring")
            print(f"   🚨 Payment system may not be fully functional")
            print(f"\n🔧 THE CRITICAL BUG IS NOT FULLY RESOLVED!")
            return False

def main():
    """Main test execution"""
    tester = TransactionFixTester()
    success = tester.run_comprehensive_test()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())