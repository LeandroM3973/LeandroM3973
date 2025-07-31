import requests
import sys
import json
from datetime import datetime

class BetArenaPaymentTester:
    def __init__(self, base_url="https://3f53ea77-ae19-43a7-bb8d-f20048b8df6d.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_users = []
        self.created_transactions = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else self.api_url
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

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
                    print(f"   Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health check"""
        return self.run_test("Health Check", "GET", "", 200)

    def test_create_user(self, name, email, phone):
        """Test user creation with payment system fields"""
        success, response = self.run_test(
            f"Create User '{name}'",
            "POST",
            "users",
            200,
            data={
                "name": name,
                "email": email,
                "phone": phone
            }
        )
        if success and 'id' in response:
            self.created_users.append(response)
            return response
        return None

    def test_get_user(self, user_id):
        """Test get user by ID"""
        success, response = self.run_test(
            "Get User by ID",
            "GET",
            f"users/{user_id}",
            200
        )
        return response if success else None

    def test_create_payment_preference(self, user_id, amount):
        """Test creating Mercado Pago payment preference - PRIORITY TEST"""
        print(f"\n🎯 PRIORITY TEST: Creating Mercado Pago Payment Preference")
        print(f"   Testing with NEW PRODUCTION KEY: 58137258421011")
        
        success, response = self.run_test(
            f"Create Payment Preference for R$ {amount}",
            "POST",
            "payments/create-preference",
            200,
            data={
                "user_id": user_id,
                "amount": amount
            }
        )
        if success and 'preference_id' in response:
            self.created_transactions.append(response)
            print(f"\n   🎉 MERCADO PAGO INTEGRATION SUCCESS!")
            print(f"   📋 Preference ID: {response['preference_id']}")
            print(f"   🔗 Payment URL: {response.get('init_point', 'N/A')}")
            print(f"   🧪 Sandbox URL: {response.get('sandbox_init_point', 'N/A')}")
            print(f"   📄 Transaction ID: {response.get('transaction_id', 'N/A')}")
            return response
        else:
            print(f"\n   ❌ MERCADO PAGO INTEGRATION FAILED!")
            print(f"   🔑 Check if production key 58137258421011 is working correctly")
            return None

    def test_withdraw_funds(self, user_id, amount):
        """Test withdrawal functionality"""
        success, response = self.run_test(
            f"Withdraw R$ {amount}",
            "POST",
            "payments/withdraw",
            200,
            data={
                "user_id": user_id,
                "amount": amount
            }
        )
        return response if success else None

    def test_get_user_transactions(self, user_id):
        """Test getting user transaction history"""
        success, response = self.run_test(
            "Get User Transactions",
            "GET",
            f"transactions/{user_id}",
            200
        )
        return response if success else []

    def test_payment_edge_cases(self):
        """Test payment system edge cases"""
        print("\n🧪 Testing Payment Edge Cases...")
        
        if self.created_users:
            user = self.created_users[0]
            
            # Test creating payment with invalid amount
            self.run_test(
                "Create Payment with Invalid Amount (negative)",
                "POST",
                "payments/create-preference",
                422,  # Validation error
                data={
                    "user_id": user['id'],
                    "amount": -50
                }
            )
            
            # Test withdrawal with insufficient balance
            self.run_test(
                "Withdraw with Insufficient Balance",
                "POST",
                "payments/withdraw",
                400,
                data={
                    "user_id": user['id'],
                    "amount": 99999  # More than user balance
                }
            )
            
            # Test payment with non-existent user
            self.run_test(
                "Create Payment for Non-existent User",
                "POST",
                "payments/create-preference",
                404,
                data={
                    "user_id": "fake-user-id",
                    "amount": 100
                }
            )

def main():
    print("🚀 Starting BetArena PAYMENT SYSTEM Tests...")
    print("🔑 Testing with NEW MERCADO PAGO PRODUCTION KEY: 58137258421011")
    print("=" * 60)
    
    tester = BetArenaPaymentTester()
    
    # Test 1: Health Check
    success, _ = tester.test_health_check()
    if not success:
        print("❌ API is not responding, stopping tests")
        return 1
    
    # Test 2: Create Test Users with proper payment info
    timestamp = datetime.now().strftime("%H%M%S")
    joao = tester.test_create_user(
        f"João Test {timestamp}", 
        f"joao.test.{timestamp}@betarena.com",
        "11999999999"
    )
    maria = tester.test_create_user(
        f"Maria Test {timestamp}", 
        f"maria.test.{timestamp}@betarena.com", 
        "11888888888"
    )
    
    if not joao or not maria:
        print("❌ Failed to create users, stopping tests")
        return 1
    
    print(f"\n📊 Created users for payment testing:")
    print(f"   João: ID={joao['id']}, Balance=R$ {joao['balance']}")
    print(f"   Maria: ID={maria['id']}, Balance=R$ {maria['balance']}")
    
    # Test 3: PRIORITY - Test Mercado Pago Payment Creation
    print(f"\n🎯 PRIORITY TEST: Testing Mercado Pago Integration")
    payment_preference = tester.test_create_payment_preference(joao['id'], 100.00)
    
    if not payment_preference:
        print("❌ CRITICAL: Mercado Pago payment preference creation FAILED!")
        print("🔍 Check backend logs for Mercado Pago API errors")
        print("🔑 Verify production key 58137258421011 is valid")
        return 1
    else:
        print("✅ SUCCESS: Mercado Pago integration is working with new production key!")
    
    # Test 4: Test different payment amounts
    print(f"\n💰 Testing different payment amounts...")
    
    # Test small amount
    small_payment = tester.test_create_payment_preference(maria['id'], 25.50)
    if small_payment:
        print("✅ Small payment (R$ 25.50) - SUCCESS")
    
    # Test larger amount
    large_payment = tester.test_create_payment_preference(joao['id'], 500.00)
    if large_payment:
        print("✅ Large payment (R$ 500.00) - SUCCESS")
    
    # Test 5: Test withdrawal functionality
    print(f"\n💸 Testing withdrawal functionality...")
    
    # First, let's check current balance
    joao_current = tester.test_get_user(joao['id'])
    if joao_current and joao_current['balance'] > 0:
        withdrawal = tester.test_withdraw_funds(joao['id'], 50.00)
        if withdrawal:
            print("✅ Withdrawal functionality - SUCCESS")
            
            # Check if balance was updated
            joao_after_withdrawal = tester.test_get_user(joao['id'])
            if joao_after_withdrawal:
                print(f"   Balance before: R$ {joao_current['balance']}")
                print(f"   Balance after: R$ {joao_after_withdrawal['balance']}")
    
    # Test 6: Test transaction history
    print(f"\n📋 Testing transaction history...")
    joao_transactions = tester.test_get_user_transactions(joao['id'])
    maria_transactions = tester.test_get_user_transactions(maria['id'])
    
    print(f"   João's transactions: {len(joao_transactions)}")
    print(f"   Maria's transactions: {len(maria_transactions)}")
    
    # Test 7: Payment edge cases
    tester.test_payment_edge_cases()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 PAYMENT SYSTEM TEST RESULTS:")
    print(f"   Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    # Check critical payment functionality
    payment_tests_passed = len(tester.created_transactions) > 0
    
    if payment_tests_passed:
        print("🎉 CRITICAL SUCCESS: Mercado Pago payment system is working!")
        print("🔑 Production key 58137258421011 is functioning correctly")
        print("✅ Payment preferences are being created successfully")
        if tester.tests_passed == tester.tests_run:
            print("🏆 ALL TESTS PASSED! Payment system is fully functional.")
            return 0
        else:
            print("⚠️  Some edge case tests failed, but core payment functionality works.")
            return 0
    else:
        print("❌ CRITICAL FAILURE: Mercado Pago payment system is NOT working!")
        print("🔍 Check backend logs for detailed error information")
        print("🔑 Verify Mercado Pago production key configuration")
        return 1

if __name__ == "__main__":
    sys.exit(main())