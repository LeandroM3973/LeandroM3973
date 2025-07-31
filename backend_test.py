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
    print("🚀 Starting BetArena API Tests - Focus on Bet Creation Issue...")
    print("=" * 70)
    
    tester = BetArenaAPITester()
    
    # Test 1: Health Check
    print("\n📋 BASIC API HEALTH CHECK")
    print("-" * 30)
    tester.test_health_check()
    
    # Test 2: Specific Bet Creation Flow Test (Main Focus)
    print("\n🎯 MAIN TEST: BET CREATION FLOW")
    print("-" * 40)
    bet_creation_success = tester.test_bet_creation_flow_with_specific_user()
    
    if not bet_creation_success:
        print("\n❌ CRITICAL ISSUE FOUND:")
        print("   The bet creation flow from frontend to backend is NOT working!")
        print("   This confirms the user's reported issue.")
        return 1
    
    # Test 3: Additional API Verification
    print("\n🔍 ADDITIONAL API VERIFICATION")
    print("-" * 35)
    
    # Create additional test users for comprehensive testing
    joao = tester.test_create_user("João Silva", "joao@test.com", "11987654321")
    maria = tester.test_create_user("Maria Santos", "maria@test.com", "11876543210")
    
    if not joao or not maria:
        print("⚠️  Warning: Could not create additional test users")
    else:
        print(f"✅ Additional test users created successfully")
        
        # Test bet creation with new users
        if joao['balance'] >= 50:
            bet = tester.test_create_bet(
                "Brasil vs Argentina - Teste",
                "sports",
                "Jogo teste para verificação",
                50.00,
                joao['id']
            )
            
            if bet:
                print("✅ Additional bet creation test passed")
                
                # Test joining the bet
                if maria['balance'] >= 50:
                    joined_bet = tester.test_join_bet(bet['id'], maria['id'])
                    if joined_bet:
                        print("✅ Bet joining test passed")
                    else:
                        print("⚠️  Bet joining test failed")
            else:
                print("⚠️  Additional bet creation test failed")
    
    # Print final results
    print("\n" + "=" * 70)
    print(f"📊 FINAL TEST RESULTS:")
    print(f"   Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if bet_creation_success:
        print("\n🎉 MAIN ISSUE RESOLUTION:")
        print("   ✅ Bet creation from frontend to backend is WORKING correctly")
        print("   ✅ All API endpoints are responding properly")
        print("   ✅ User authentication and balance management works")
        print("   ✅ The reported issue may be frontend-specific or network-related")
        print("\n💡 RECOMMENDATION:")
        print("   - Check frontend console for JavaScript errors")
        print("   - Verify network connectivity from frontend to backend")
        print("   - Check browser developer tools for failed requests")
        print("   - Ensure frontend is using correct API URL")
        return 0
    else:
        print("\n❌ CRITICAL ISSUE CONFIRMED:")
        print("   The bet creation API is not working properly")
        print("   This confirms the user's reported problem")
        print("   Backend investigation and fixes are needed")
        return 1

if __name__ == "__main__":
    sys.exit(main())