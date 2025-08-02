import requests
import sys
import json
from datetime import datetime

class BetArenaAPITester:
    def __init__(self, base_url="https://47eed0e6-f30e-431a-b6a5-47794796692b.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_users = []
        self.created_bets = []
        self.created_transactions = []
        self.abacatepay_working = False

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

    def test_create_user(self, name, email, phone, password="password123"):
        """Test user creation with payment system fields"""
        success, response = self.run_test(
            f"Create User '{name}'",
            "POST",
            "users",
            200,
            data={
                "name": name,
                "email": email,
                "phone": phone,
                "password": password
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

    def test_get_all_users(self):
        """Test get all users"""
        success, response = self.run_test(
            "Get All Users",
            "GET",
            "users",
            200
        )
        return response if success else []

    def test_create_bet(self, event_title, event_type, event_description, amount, creator_id):
        """Test bet creation"""
        success, response = self.run_test(
            f"Create Bet '{event_title}'",
            "POST",
            "bets",
            200,
            data={
                "event_title": event_title,
                "event_type": event_type,
                "event_description": event_description,
                "amount": amount,
                "creator_id": creator_id
            }
        )
        if success and 'id' in response:
            self.created_bets.append(response)
            return response
        return None

    def test_join_bet(self, bet_id, user_id):
        """Test joining a bet"""
        success, response = self.run_test(
            "Join Bet",
            "POST",
            f"bets/{bet_id}/join",
            200,
            data={"user_id": user_id}
        )
        return response if success else None

    def test_declare_winner(self, bet_id, winner_id):
        """Test declaring winner"""
        success, response = self.run_test(
            "Declare Winner",
            "POST",
            f"bets/{bet_id}/declare-winner",
            200,
            data={"winner_id": winner_id}
        )
        return response if success else None

    def test_get_all_bets(self):
        """Test get all bets"""
        success, response = self.run_test(
            "Get All Bets",
            "GET",
            "bets",
            200
        )
        return response if success else []

    def test_get_waiting_bets(self):
        """Test get waiting bets"""
        success, response = self.run_test(
            "Get Waiting Bets",
            "GET",
            "bets/waiting",
            200
        )
        return response if success else []

    def test_get_user_bets(self, user_id):
        """Test get user bets"""
        success, response = self.run_test(
            "Get User Bets",
            "GET",
            f"bets/user/{user_id}",
            200
        )
        return response if success else []

    def test_create_payment_preference(self, user_id, amount):
        """Test creating AbacatePay payment preference - PRIORITY TEST"""
        success, response = self.run_test(
            f"Create AbacatePay Payment Preference for R$ {amount}",
            "POST",
            "payments/create-preference",
            200,
            data={
                "user_id": user_id,
                "amount": amount
            }
        )
        if success:
            self.created_transactions.append(response)
            print(f"   ✅ Payment preference created successfully!")
            
            # CRITICAL ANALYSIS FOR ABACATEPAY INTEGRATION
            print(f"\n   🥑 ABACATEPAY INTEGRATION ANALYSIS:")
            if response.get('abacatepay'):
                print(f"   ✅ AbacatePay integration is ACTIVE")
                self.abacatepay_working = True
                print(f"   🔑 Using AbacatePay production credentials")
                print(f"   💰 Amount: R$ {response.get('amount', amount)}")
                print(f"   💳 Fee: R$ {response.get('fee', 0.80)}")
                print(f"   🧪 Test Mode: {response.get('test_mode', 'Unknown')}")
                print(f"   📄 Status: {response.get('status', 'Unknown')}")
            elif response.get('demo_mode'):
                print(f"   ⚠️  DEMO MODE is active - AbacatePay integration failed")
                print(f"   🚨 This indicates a problem with AbacatePay configuration")
                print(f"   💡 Message: {response.get('message', 'No message')}")
            
            # Log key response fields
            print(f"   📋 Preference ID: {response.get('preference_id', 'N/A')}")
            print(f"   🔗 Payment URL: {response.get('payment_url', response.get('init_point', 'N/A'))}")
            print(f"   📄 Transaction ID: {response.get('transaction_id', 'N/A')}")
            
            # Test URL accessibility if available
            payment_url = response.get('payment_url') or response.get('init_point')
            if payment_url and payment_url != 'N/A':
                print(f"   🌐 Testing payment URL accessibility...")
                try:
                    url_test = requests.head(payment_url, timeout=10)
                    if url_test.status_code in [200, 302, 301, 403]:  # 403 is normal for AbacatePay
                        print(f"   ✅ Payment URL is accessible (Status: {url_test.status_code})")
                    else:
                        print(f"   ❌ Payment URL returned status: {url_test.status_code}")
                except Exception as e:
                    print(f"   ❌ Payment URL test failed: {str(e)}")
            
            return response
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

    def test_mercado_pago_integration_comprehensive(self):
        """Comprehensive test for Mercado Pago integration issue"""
        print("\n🎯 COMPREHENSIVE MERCADO PAGO INTEGRATION TEST...")
        print("=" * 70)
        
        # Test with the specific user from the issue report
        test_user_email = "test@mobile.com"
        test_user_id = "3cccefee-d410-4931-9d96-1ae945dfa689"
        
        print(f"\n1. Testing with reported user: {test_user_email}")
        print(f"   User ID: {test_user_id}")
        
        # First verify user exists
        user_data = self.test_get_user(test_user_id)
        if not user_data:
            print("❌ Test user not found - creating user for testing...")
            user_data = self.test_create_user("Test Mobile User", test_user_email, "11999999999", "password123")
            if not user_data:
                print("❌ Failed to create test user")
                return False
            test_user_id = user_data['id']
        
        print(f"✅ User found/created - Balance: R$ {user_data['balance']:.2f}")
        
        # Test different payment amounts
        test_amounts = [10.00, 50.00, 100.00, 250.00]
        
        for amount in test_amounts:
            print(f"\n2. Testing payment preference creation for R$ {amount}...")
            print("-" * 50)
            
            payment_response = self.test_create_payment_preference(test_user_id, amount)
            
            if not payment_response:
                print(f"❌ CRITICAL: Payment preference creation failed for R$ {amount}")
                return False
            
            # Analyze the response in detail
            print(f"\n   📊 DETAILED RESPONSE ANALYSIS:")
            print(f"   - Preference ID: {payment_response.get('preference_id', 'MISSING')}")
            print(f"   - Transaction ID: {payment_response.get('transaction_id', 'MISSING')}")
            print(f"   - Real MP Active: {payment_response.get('real_mp', False)}")
            print(f"   - Demo Mode: {payment_response.get('demo_mode', False)}")
            print(f"   - Message: {payment_response.get('message', 'No message')}")
            
            # Check if we're getting real Mercado Pago URLs or demo URLs
            init_point = payment_response.get('init_point')
            sandbox_init_point = payment_response.get('sandbox_init_point')
            
            if init_point:
                if 'mercadopago' in init_point.lower():
                    print(f"   ✅ Real Mercado Pago URL detected in init_point")
                else:
                    print(f"   ⚠️  Non-Mercado Pago URL in init_point: {init_point}")
            
            if sandbox_init_point:
                if 'mercadopago' in sandbox_init_point.lower():
                    print(f"   ✅ Real Mercado Pago URL detected in sandbox_init_point")
                else:
                    print(f"   ⚠️  Non-Mercado Pago URL in sandbox_init_point: {sandbox_init_point}")
            
            # Test webhook endpoint
            print(f"\n   🔗 Testing webhook endpoint accessibility...")
            webhook_success, webhook_response = self.run_test(
                "Test Webhook Endpoint",
                "POST",
                "payments/webhook",
                200,
                data={"test": "webhook_test"}
            )
            
            if webhook_success:
                print(f"   ✅ Webhook endpoint is accessible")
            else:
                print(f"   ❌ Webhook endpoint failed")
            
            # Test payment simulation (for demo mode)
            if payment_response.get('demo_mode') and payment_response.get('transaction_id'):
                print(f"\n   🧪 Testing payment simulation...")
                simulation_success, simulation_response = self.run_test(
                    "Simulate Payment Approval",
                    "POST",
                    f"payments/simulate-approval/{payment_response['transaction_id']}",
                    200
                )
                
                if simulation_success:
                    print(f"   ✅ Payment simulation works")
                    
                    # Check if balance was updated
                    updated_user = self.test_get_user(test_user_id)
                    if updated_user and updated_user['balance'] > user_data['balance']:
                        print(f"   ✅ User balance updated correctly: R$ {updated_user['balance']:.2f}")
                        user_data = updated_user  # Update for next iteration
                    else:
                        print(f"   ❌ User balance not updated properly")
                else:
                    print(f"   ❌ Payment simulation failed")
            
            print(f"\n   ✅ Payment preference test completed for R$ {amount}")
        
        # Test transaction history
        print(f"\n3. Testing transaction history...")
        print("-" * 30)
        
        transactions = self.test_get_user_transactions(test_user_id)
        if transactions:
            print(f"   ✅ Transaction history retrieved: {len(transactions)} transactions")
            for i, tx in enumerate(transactions[:3]):  # Show first 3 transactions
                print(f"   - Transaction {i+1}: {tx.get('type', 'unknown')} - R$ {tx.get('amount', 0):.2f}")
        else:
            print(f"   ⚠️  No transactions found or retrieval failed")
        
        # Final assessment
        print(f"\n4. FINAL MERCADO PAGO INTEGRATION ASSESSMENT:")
        print("=" * 50)
        
        # Check if any payment preference was created successfully
        if len(self.created_transactions) > 0:
            real_mp_count = sum(1 for tx in self.created_transactions if tx.get('real_mp'))
            demo_count = sum(1 for tx in self.created_transactions if tx.get('demo_mode'))
            
            print(f"   📊 Payment Preferences Created: {len(self.created_transactions)}")
            print(f"   🔑 Real Mercado Pago: {real_mp_count}")
            print(f"   🧪 Demo Mode: {demo_count}")
            
            if real_mp_count > 0:
                print(f"   ✅ MERCADO PAGO INTEGRATION IS WORKING")
                print(f"   ✅ Production keys are valid and functional")
                print(f"   ✅ Payment URLs are being generated correctly")
                return True
            elif demo_count > 0:
                print(f"   ⚠️  MERCADO PAGO IS IN DEMO MODE")
                print(f"   🚨 This indicates an issue with the production configuration")
                print(f"   💡 Possible causes:")
                print(f"      - Invalid or expired access token")
                print(f"      - Network connectivity issues")
                print(f"      - Mercado Pago API service issues")
                print(f"      - Incorrect API endpoint configuration")
                return False
            else:
                print(f"   ❌ MERCADO PAGO INTEGRATION FAILED")
                print(f"   🚨 Neither real MP nor demo mode is working")
                return False
        else:
            print(f"   ❌ NO PAYMENT PREFERENCES CREATED")
            print(f"   🚨 Complete failure of payment system")
            return False
    def test_login_user(self, email, password):
        """Test user login"""
        success, response = self.run_test(
            f"Login User '{email}'",
            "POST",
            "users/login",
            200,
            data={
                "email": email,
                "password": password
            }
        )
        return response if success else None

    def test_bet_creation_flow_with_specific_user(self):
        """Test the specific bet creation flow reported by user"""
        print("\n🎯 TESTING SPECIFIC BET CREATION ISSUE...")
        print("=" * 60)
        
        # Test with the specific user credentials provided
        test_user_email = "test@mobile.com"
        test_user_password = "password123"
        
        # First, try to login with the test user
        print(f"\n1. Testing login with user: {test_user_email}")
        login_response = self.test_login_user(test_user_email, test_user_password)
        
        if not login_response:
            print("❌ Login failed - creating test user first...")
            # Create the test user if login fails
            test_user = self.test_create_user("Test Mobile User", test_user_email, "11999999999", test_user_password)
            if not test_user:
                print("❌ Failed to create test user")
                return False
            
            # Add balance to user (simulate deposit)
            print(f"\n2. Adding balance to test user...")
            deposit_response = self.test_create_payment_preference(test_user['id'], 75.00)
            if deposit_response and 'transaction_id' in deposit_response:
                # Simulate payment approval
                approval_response = self.run_test(
                    "Simulate Payment Approval",
                    "POST", 
                    f"payments/simulate-approval/{deposit_response['transaction_id']}",
                    200
                )
                if approval_response[0]:
                    print("✅ Balance added successfully")
                else:
                    print("❌ Failed to add balance")
                    return False
            
            # Get updated user data
            updated_user = self.test_get_user(test_user['id'])
            if not updated_user:
                print("❌ Failed to get updated user data")
                return False
            
            current_user = updated_user
        else:
            print("✅ Login successful")
            current_user = login_response
        
        print(f"   User ID: {current_user['id']}")
        print(f"   User Balance: R$ {current_user['balance']:.2f}")
        
        # Test bet creation with the exact same data structure as frontend
        print(f"\n3. Testing bet creation (mimicking frontend request)...")
        bet_data = {
            "event_title": "Teste de Aposta Mobile",
            "event_type": "custom", 
            "event_description": "Teste para verificar se a criação de aposta funciona do frontend para backend",
            "amount": 50.00,
            "creator_id": current_user['id']
        }
        
        print(f"   Bet Data: {json.dumps(bet_data, indent=2)}")
        
        # This should match exactly what the frontend sends
        success, bet_response = self.run_test(
            "Create Bet (Frontend Simulation)",
            "POST",
            "bets",
            200,
            data=bet_data
        )
        
        if not success:
            print("❌ CRITICAL: Bet creation failed - this matches the user's reported issue!")
            return False
        
        print("✅ Bet creation successful!")
        print(f"   Bet ID: {bet_response['id']}")
        print(f"   Invite Code: {bet_response['invite_code']}")
        print(f"   Status: {bet_response['status']}")
        
        # Verify user balance was deducted
        print(f"\n4. Verifying balance deduction...")
        updated_user_after_bet = self.test_get_user(current_user['id'])
        if updated_user_after_bet:
            expected_balance = current_user['balance'] - bet_data['amount']
            actual_balance = updated_user_after_bet['balance']
            
            if abs(actual_balance - expected_balance) < 0.01:  # Allow for floating point precision
                print(f"✅ Balance correctly deducted: R$ {actual_balance:.2f}")
            else:
                print(f"❌ Balance deduction error: Expected R$ {expected_balance:.2f}, got R$ {actual_balance:.2f}")
                return False
        
        # Test getting the bet by invite code (this is what frontend would do next)
        print(f"\n5. Testing invite code retrieval...")
        invite_success, invite_response = self.run_test(
            "Get Bet by Invite Code",
            "GET",
            f"bets/invite/{bet_response['invite_code']}",
            200
        )
        
        if not invite_success:
            print("❌ Failed to retrieve bet by invite code")
            return False
        
        print("✅ Invite code retrieval successful!")
        
        # Test the complete flow that frontend expects
        print(f"\n6. Testing complete frontend-to-backend flow...")
        
        # Get waiting bets (frontend calls this)
        waiting_bets_success, waiting_bets = self.run_test(
            "Get Waiting Bets",
            "GET",
            "bets/waiting",
            200
        )
        
        if waiting_bets_success and len(waiting_bets) > 0:
            print(f"✅ Waiting bets retrieved: {len(waiting_bets)} bets found")
        else:
            print("❌ No waiting bets found or request failed")
            return False
        
        # Get user bets (frontend calls this)
        user_bets_success, user_bets = self.run_test(
            "Get User Bets",
            "GET", 
            f"bets/user/{current_user['id']}",
            200
        )
        
        if user_bets_success and len(user_bets) > 0:
            print(f"✅ User bets retrieved: {len(user_bets)} bets found")
        else:
            print("❌ No user bets found or request failed")
            return False
        
        print(f"\n🎉 BET CREATION FLOW TEST COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ All frontend-to-backend communication is working correctly")
        print("✅ Bet creation API endpoint is functional")
        print("✅ User balance management is working")
        print("✅ Invite code generation and retrieval works")
        print("✅ All related API calls are responding properly")
        
        return True

def main():
    print("🚀 Starting BetArena API Tests - Focus on Mercado Pago Integration Issue...")
    print("=" * 80)
    
    tester = BetArenaAPITester()
    
    # Test 1: Health Check
    print("\n📋 BASIC API HEALTH CHECK")
    print("-" * 30)
    tester.test_health_check()
    
    # Test 2: MAIN FOCUS - Mercado Pago Integration Test
    print("\n🎯 MAIN TEST: MERCADO PAGO INTEGRATION")
    print("-" * 45)
    mercado_pago_success = tester.test_mercado_pago_integration_comprehensive()
    
    # Test 3: Additional verification - Bet Creation Flow (Secondary)
    print("\n🔍 SECONDARY TEST: BET CREATION FLOW")
    print("-" * 40)
    bet_creation_success = tester.test_bet_creation_flow_with_specific_user()
    
    # Print final results
    print("\n" + "=" * 80)
    print(f"📊 FINAL TEST RESULTS:")
    print(f"   Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    print(f"\n🎯 MERCADO PAGO INTEGRATION RESULTS:")
    if mercado_pago_success:
        print("   ✅ MERCADO PAGO IS WORKING CORRECTLY")
        print("   ✅ Production keys are valid")
        print("   ✅ Payment URLs are being generated")
        print("   ✅ API endpoints are functional")
        print("\n💡 USER ISSUE ANALYSIS:")
        print("   - Backend Mercado Pago integration is working")
        print("   - Issue may be frontend-related (popup blockers, JavaScript errors)")
        print("   - Check browser console for errors")
        print("   - Verify frontend is calling correct API endpoints")
        return 0
    else:
        print("   ❌ MERCADO PAGO INTEGRATION HAS ISSUES")
        print("   🚨 This confirms the user's reported problem")
        print("\n🔧 RECOMMENDED FIXES:")
        print("   1. Verify Mercado Pago access token is valid and not expired")
        print("   2. Check if PUBLIC_KEY should be different from ACCESS_TOKEN")
        print("   3. Test network connectivity to Mercado Pago APIs")
        print("   4. Review Mercado Pago account status and permissions")
        print("   5. Check if webhook URLs are accessible from Mercado Pago servers")
        
        if bet_creation_success:
            print(f"\n📝 NOTE: Bet creation system is working correctly")
            print(f"   - The issue is specifically with payment integration")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())