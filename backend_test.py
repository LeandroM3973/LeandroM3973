import requests
import sys
import json
from datetime import datetime

class BetArenaAPITester:
    def __init__(self, base_url="https://3f53ea77-ae19-43a7-bb8d-f20048b8df6d.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_users = []
        self.created_bets = []
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
        """Test creating Mercado Pago payment preference - PRIORITY TEST"""
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
            print(f"   ✅ Payment preference created successfully!")
            print(f"   📋 Preference ID: {response['preference_id']}")
            print(f"   🔗 Payment URL: {response.get('init_point', 'N/A')}")
            print(f"   🧪 Sandbox URL: {response.get('sandbox_init_point', 'N/A')}")
            print(f"   📄 Transaction ID: {response.get('transaction_id', 'N/A')}")
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
    print("🚀 Starting BetArena API Tests...")
    print("=" * 50)
    
    tester = BetArenaAPITester()
    
    # Test 1: Health Check
    tester.test_health_check()
    
    # Test 2: Create Users
    joao = tester.test_create_user("João")
    maria = tester.test_create_user("Maria")
    
    if not joao or not maria:
        print("❌ Failed to create users, stopping tests")
        return 1
    
    print(f"\n📊 Created users:")
    print(f"   João: ID={joao['id']}, Balance={joao['balance']}")
    print(f"   Maria: ID={maria['id']}, Balance={maria['balance']}")
    
    # Test 3: Verify user creation and balance
    if joao['balance'] != 1000 or maria['balance'] != 1000:
        print("❌ Users don't have correct starting balance of 1000")
        return 1
    
    # Test 4: Get user by ID
    joao_retrieved = tester.test_get_user(joao['id'])
    if not joao_retrieved or joao_retrieved['name'] != 'João':
        print("❌ Failed to retrieve user by ID")
        return 1
    
    # Test 5: Get all users
    all_users = tester.test_get_all_users()
    if len(all_users) < 2:
        print("❌ Failed to get all users")
        return 1
    
    # Test 6: Create bet
    bet = tester.test_create_bet(
        "Brasil vs Argentina",
        "sports",
        "Copa do Mundo - Final",
        200,
        joao['id']
    )
    
    if not bet:
        print("❌ Failed to create bet")
        return 1
    
    print(f"\n📊 Created bet:")
    print(f"   ID: {bet['id']}")
    print(f"   Title: {bet['event_title']}")
    print(f"   Amount: {bet['amount']}")
    print(f"   Status: {bet['status']}")
    
    # Test 7: Verify João's balance was deducted
    joao_after_bet = tester.test_get_user(joao['id'])
    if joao_after_bet['balance'] != 800:  # 1000 - 200
        print(f"❌ João's balance should be 800, but is {joao_after_bet['balance']}")
        return 1
    
    # Test 8: Get waiting bets
    waiting_bets = tester.test_get_waiting_bets()
    if len(waiting_bets) == 0:
        print("❌ No waiting bets found")
        return 1
    
    # Test 9: Maria joins the bet
    joined_bet = tester.test_join_bet(bet['id'], maria['id'])
    if not joined_bet or joined_bet['status'] != 'active':
        print("❌ Failed to join bet or bet status not active")
        return 1
    
    # Test 10: Verify Maria's balance was deducted
    maria_after_join = tester.test_get_user(maria['id'])
    if maria_after_join['balance'] != 800:  # 1000 - 200
        print(f"❌ Maria's balance should be 800, but is {maria_after_join['balance']}")
        return 1
    
    # Test 11: Declare João as winner
    completed_bet = tester.test_declare_winner(bet['id'], joao['id'])
    if not completed_bet or completed_bet['status'] != 'completed':
        print("❌ Failed to declare winner or bet status not completed")
        return 1
    
    # Test 12: Verify final balances
    joao_final = tester.test_get_user(joao['id'])
    maria_final = tester.test_get_user(maria['id'])
    
    expected_joao_balance = 800 + (200 * 2)  # 800 + 400 = 1200
    expected_maria_balance = 800  # Lost the bet
    
    if joao_final['balance'] != expected_joao_balance:
        print(f"❌ João's final balance should be {expected_joao_balance}, but is {joao_final['balance']}")
        return 1
    
    if maria_final['balance'] != expected_maria_balance:
        print(f"❌ Maria's final balance should be {expected_maria_balance}, but is {maria_final['balance']}")
        return 1
    
    print(f"\n🎉 Final balances correct:")
    print(f"   João: {joao_final['balance']} pontos (won)")
    print(f"   Maria: {maria_final['balance']} pontos (lost)")
    
    # Test 13: Get user bets
    joao_bets = tester.test_get_user_bets(joao['id'])
    maria_bets = tester.test_get_user_bets(maria['id'])
    
    if len(joao_bets) == 0 or len(maria_bets) == 0:
        print("❌ Failed to get user bets")
        return 1
    
    # Test 14: Get all bets
    all_bets = tester.test_get_all_bets()
    if len(all_bets) == 0:
        print("❌ Failed to get all bets")
        return 1
    
    # Test 15: Edge cases
    tester.test_edge_cases()
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 FINAL RESULTS:")
    print(f"   Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 ALL TESTS PASSED! Backend API is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())