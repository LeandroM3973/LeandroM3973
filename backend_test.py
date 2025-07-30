import requests
import sys
import json
from datetime import datetime

class BetArenaAPITester:
    def __init__(self, base_url="https://0ac7c639-df83-47f0-8ae3-29a1c25d3a76.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_users = []
        self.created_bets = []

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

    def test_create_user(self, name):
        """Test user creation"""
        success, response = self.run_test(
            f"Create User '{name}'",
            "POST",
            "users",
            200,
            data={"name": name}
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

    def test_edge_cases(self):
        """Test edge cases and validations"""
        print("\n🧪 Testing Edge Cases...")
        
        # Test creating bet with insufficient balance
        if self.created_users:
            user = self.created_users[0]
            self.run_test(
                "Create Bet with Insufficient Balance",
                "POST",
                "bets",
                400,
                data={
                    "event_title": "Expensive Bet",
                    "event_type": "custom",
                    "event_description": "This bet costs more than user balance",
                    "amount": 2000,  # More than 1000 starting balance
                    "creator_id": user['id']
                }
            )

        # Test joining non-existent bet
        self.run_test(
            "Join Non-existent Bet",
            "POST",
            "bets/fake-bet-id/join",
            404,
            data={"user_id": "fake-user-id"}
        )

        # Test getting non-existent user
        self.run_test(
            "Get Non-existent User",
            "GET",
            "users/fake-user-id",
            404
        )

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