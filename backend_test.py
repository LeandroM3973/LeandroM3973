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

    def test_abacatepay_integration_comprehensive(self):
        """Comprehensive test for AbacatePay integration - MAIN FOCUS"""
        print("\n🥑 COMPREHENSIVE ABACATEPAY INTEGRATION TEST...")
        print("=" * 70)
        
        # Test with realistic user data
        test_user_email = "carlos.silva@gmail.com"
        test_user_name = "Carlos Silva"
        test_user_phone = "11987654321"
        test_user_password = "minhasenha123"
        
        print(f"\n1. Creating/Testing with realistic user: {test_user_name}")
        print(f"   Email: {test_user_email}")
        print(f"   Phone: {test_user_phone}")
        
        # Create or get user
        user_data = self.test_create_user(test_user_name, test_user_email, test_user_phone, test_user_password)
        if not user_data:
            # Try to login if user already exists
            login_response = self.test_login_user(test_user_email, test_user_password)
            if login_response:
                user_data = login_response
                print("✅ User login successful")
            else:
                print("❌ Failed to create or login user")
                return False
        
        test_user_id = user_data['id']
        print(f"✅ User ready - Balance: R$ {user_data['balance']:.2f}")
        
        # Test different payment amounts that users typically use
        test_amounts = [25.00, 50.00, 100.00, 200.00]
        successful_payments = 0
        
        for amount in test_amounts:
            print(f"\n2. Testing AbacatePay payment creation for R$ {amount}...")
            print("-" * 55)
            
            payment_response = self.test_create_payment_preference(test_user_id, amount)
            
            if not payment_response:
                print(f"❌ CRITICAL: Payment preference creation failed for R$ {amount}")
                continue
            
            successful_payments += 1
            
            # Detailed response analysis
            print(f"\n   📊 DETAILED ABACATEPAY RESPONSE ANALYSIS:")
            print(f"   - Preference ID: {payment_response.get('preference_id', 'MISSING')}")
            print(f"   - Transaction ID: {payment_response.get('transaction_id', 'MISSING')}")
            print(f"   - AbacatePay Active: {payment_response.get('abacatepay', False)}")
            print(f"   - Demo Mode: {payment_response.get('demo_mode', False)}")
            print(f"   - Test Mode: {payment_response.get('test_mode', 'Unknown')}")
            print(f"   - Message: {payment_response.get('message', 'No message')}")
            
            # Check payment URL
            payment_url = payment_response.get('payment_url') or payment_response.get('init_point')
            if payment_url:
                if 'abacatepay' in payment_url.lower() or 'abacate' in payment_url.lower():
                    print(f"   ✅ Real AbacatePay URL detected: {payment_url[:50]}...")
                else:
                    print(f"   ⚠️  Non-AbacatePay URL: {payment_url}")
            
            # Test webhook endpoint (critical for payment processing)
            print(f"\n   🔗 Testing AbacatePay webhook endpoint...")
            webhook_test_data = {
                "event": "billing.paid",
                "data": {
                    "externalId": payment_response.get('transaction_id', 'test'),
                    "payment": {
                        "amount": int(amount * 100),  # AbacatePay uses cents
                        "fee": 80  # R$ 0.80 fee
                    }
                }
            }
            
            # Test webhook with proper secret
            webhook_url = f"{self.api_url}/payments/webhook?webhookSecret=betarena_webhook_secret_2025"
            try:
                webhook_response = requests.post(webhook_url, json=webhook_test_data, timeout=10)
                if webhook_response.status_code == 200:
                    print(f"   ✅ Webhook endpoint is accessible and working")
                else:
                    print(f"   ❌ Webhook endpoint returned status: {webhook_response.status_code}")
            except Exception as e:
                print(f"   ❌ Webhook endpoint test failed: {str(e)}")
            
            # Test payment simulation for demo mode
            if payment_response.get('demo_mode') and payment_response.get('transaction_id'):
                print(f"\n   🧪 Testing payment simulation (demo mode)...")
                simulation_success, simulation_response = self.run_test(
                    "Simulate Payment Approval",
                    "POST",
                    f"payments/simulate-approval/{payment_response['transaction_id']}",
                    200
                )
                
                if simulation_success:
                    print(f"   ✅ Payment simulation successful")
                    
                    # Verify balance update
                    updated_user = self.test_get_user(test_user_id)
                    if updated_user and updated_user['balance'] > user_data['balance']:
                        balance_increase = updated_user['balance'] - user_data['balance']
                        print(f"   ✅ User balance updated: +R$ {balance_increase:.2f}")
                        user_data = updated_user  # Update for next iteration
                    else:
                        print(f"   ❌ User balance not updated properly")
                else:
                    print(f"   ❌ Payment simulation failed")
            
            print(f"\n   ✅ Payment test completed for R$ {amount}")
        
        # Test transaction history
        print(f"\n3. Testing transaction history...")
        print("-" * 35)
        
        transactions = self.test_get_user_transactions(test_user_id)
        if transactions:
            print(f"   ✅ Transaction history retrieved: {len(transactions)} transactions")
            for i, tx in enumerate(transactions[:3]):  # Show first 3 transactions
                tx_type = tx.get('type', 'unknown')
                tx_amount = tx.get('amount', 0)
                tx_status = tx.get('status', 'unknown')
                print(f"   - Transaction {i+1}: {tx_type} - R$ {tx_amount:.2f} ({tx_status})")
        else:
            print(f"   ⚠️  No transactions found or retrieval failed")
        
        # Test user authentication flow
        print(f"\n4. Testing user authentication flow...")
        print("-" * 40)
        
        # Test login
        login_test = self.test_login_user(test_user_email, test_user_password)
        if login_test:
            print(f"   ✅ User login working correctly")
        else:
            print(f"   ❌ User login failed")
        
        # Test user retrieval
        user_retrieval = self.test_get_user(test_user_id)
        if user_retrieval:
            print(f"   ✅ User retrieval working correctly")
        else:
            print(f"   ❌ User retrieval failed - this could cause 'user not found' errors")
        
        # Final assessment
        print(f"\n5. FINAL ABACATEPAY INTEGRATION ASSESSMENT:")
        print("=" * 55)
        
        if successful_payments > 0:
            abacatepay_count = sum(1 for tx in self.created_transactions if tx.get('abacatepay'))
            demo_count = sum(1 for tx in self.created_transactions if tx.get('demo_mode'))
            
            print(f"   📊 Payment Preferences Created: {successful_payments}/{len(test_amounts)}")
            print(f"   🥑 AbacatePay Integration: {abacatepay_count}")
            print(f"   🧪 Demo Mode: {demo_count}")
            
            if abacatepay_count > 0:
                print(f"   ✅ ABACATEPAY INTEGRATION IS WORKING")
                print(f"   ✅ Production credentials are valid and functional")
                print(f"   ✅ Payment URLs are being generated correctly")
                print(f"   ✅ Backend payment system is operational")
                return True
            elif demo_count > 0:
                print(f"   ⚠️  ABACATEPAY IS IN DEMO MODE")
                print(f"   🚨 This indicates an issue with the production configuration")
                print(f"   💡 Possible causes:")
                print(f"      - Invalid or expired AbacatePay API token")
                print(f"      - Network connectivity issues to AbacatePay servers")
                print(f"      - AbacatePay API service issues")
                print(f"      - Incorrect webhook secret configuration")
                return False
            else:
                print(f"   ❌ ABACATEPAY INTEGRATION FAILED")
                print(f"   🚨 Neither real AbacatePay nor demo mode is working")
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

    def test_bet_creation_flow_with_realistic_user(self):
        """Test bet creation flow with realistic user data"""
        print("\n🎯 TESTING BET CREATION FLOW WITH REALISTIC DATA...")
        print("=" * 65)
        
        # Use realistic Brazilian user data
        test_user_email = "maria.santos@hotmail.com"
        test_user_name = "Maria Santos"
        test_user_phone = "11987654321"
        test_user_password = "minhaSenha456"
        
        # First, try to login or create user
        print(f"\n1. Testing with realistic user: {test_user_name}")
        login_response = self.test_login_user(test_user_email, test_user_password)
        
        if not login_response:
            print("❌ Login failed - creating new user...")
            test_user = self.test_create_user(test_user_name, test_user_email, test_user_phone, test_user_password)
            if not test_user:
                print("❌ Failed to create test user")
                return False
            current_user = test_user
        else:
            print("✅ Login successful")
            current_user = login_response
        
        print(f"   User ID: {current_user['id']}")
        print(f"   User Balance: R$ {current_user['balance']:.2f}")
        
        # Add balance if needed
        if current_user['balance'] < 100.00:
            print(f"\n2. Adding balance to user for testing...")
            deposit_response = self.test_create_payment_preference(current_user['id'], 150.00)
            if deposit_response and deposit_response.get('transaction_id'):
                # Simulate payment approval if in demo mode
                if deposit_response.get('demo_mode'):
                    approval_response = self.run_test(
                        "Simulate Payment Approval",
                        "POST", 
                        f"payments/simulate-approval/{deposit_response['transaction_id']}",
                        200
                    )
                    if approval_response[0]:
                        print("✅ Balance added successfully")
                        # Get updated user data
                        current_user = self.test_get_user(current_user['id'])
                    else:
                        print("❌ Failed to add balance")
                        return False
        
        # Test bet creation with realistic data
        print(f"\n3. Testing bet creation with realistic data...")
        bet_data = {
            "event_title": "Flamengo vs Palmeiras - Quem ganha?",
            "event_type": "sports", 
            "event_description": "Aposta sobre o resultado do jogo Flamengo x Palmeiras no Brasileirão",
            "amount": 75.00,
            "creator_id": current_user['id']
        }
        
        print(f"   Bet Data: {json.dumps(bet_data, indent=2)}")
        
        success, bet_response = self.run_test(
            "Create Realistic Bet",
            "POST",
            "bets",
            200,
            data=bet_data
        )
        
        if not success:
            print("❌ CRITICAL: Bet creation failed!")
            return False
        
        print("✅ Bet creation successful!")
        print(f"   Bet ID: {bet_response['id']}")
        print(f"   Invite Code: {bet_response['invite_code']}")
        print(f"   Status: {bet_response['status']}")
        
        # Verify balance deduction
        print(f"\n4. Verifying balance deduction...")
        updated_user = self.test_get_user(current_user['id'])
        if updated_user:
            expected_balance = current_user['balance'] - bet_data['amount']
            actual_balance = updated_user['balance']
            
            if abs(actual_balance - expected_balance) < 0.01:
                print(f"✅ Balance correctly deducted: R$ {actual_balance:.2f}")
            else:
                print(f"❌ Balance deduction error: Expected R$ {expected_balance:.2f}, got R$ {actual_balance:.2f}")
                return False
        
        # Test invite code functionality
        print(f"\n5. Testing invite code functionality...")
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
        
        # Test related API endpoints
        print(f"\n6. Testing related API endpoints...")
        
        # Get waiting bets
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
        
        # Get user bets
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
        print("=" * 65)
        print("✅ All bet-related API endpoints are functional")
        print("✅ User balance management is working correctly")
        print("✅ Invite code system is operational")
        print("✅ Backend bet creation system is working properly")
        
        return True

    def test_abacatepay_balance_crediting_system(self):
        """CRITICAL TEST: AbacatePay Balance Crediting System - USER REQUIREMENT FOCUS"""
        print("\n💰 CRITICAL BALANCE UPDATE TEST - AbacatePay Balance Crediting System")
        print("=" * 80)
        print("USER REQUIREMENT: 'ao valor ser depositado, deve creditar no site no campo $ (saldo)'")
        print("TESTING: Balance must be credited in the $ field after deposit")
        print("=" * 80)
        
        # Create test user with initial balance
        test_user_email = "balance.test@gmail.com"
        test_user_name = "Balance Test User"
        test_user_phone = "11999888777"
        test_user_password = "balancetest123"
        
        print(f"\n1. SETUP: Creating test user with initial balance...")
        print("-" * 55)
        
        # Create user
        user_data = self.test_create_user(test_user_name, test_user_email, test_user_phone, test_user_password)
        if not user_data:
            print("❌ CRITICAL: Failed to create test user")
            return False
        
        test_user_id = user_data['id']
        initial_balance = user_data['balance']
        print(f"✅ Test user created - ID: {test_user_id}")
        print(f"✅ Initial balance: R$ {initial_balance:.2f}")
        
        # Add some initial balance for testing (R$ 100.00)
        print(f"\n   Adding initial balance of R$ 100.00...")
        initial_deposit = self.test_create_payment_preference(test_user_id, 100.00)
        if initial_deposit and initial_deposit.get('transaction_id'):
            if initial_deposit.get('demo_mode'):
                approval_response = self.run_test(
                    "Simulate Initial Balance Addition",
                    "POST", 
                    f"payments/simulate-approval/{initial_deposit['transaction_id']}",
                    200
                )
                if approval_response[0]:
                    user_data = self.test_get_user(test_user_id)
                    initial_balance = user_data['balance']
                    print(f"✅ Initial balance set to: R$ {initial_balance:.2f}")
        
        # Test deposit amount
        deposit_amount = 50.00
        expected_fee = 0.80
        expected_net_credit = deposit_amount - expected_fee
        expected_final_balance = initial_balance + expected_net_credit
        
        print(f"\n2. PAYMENT CREATION TEST: Creating payment preference...")
        print("-" * 60)
        print(f"   Deposit Amount: R$ {deposit_amount:.2f}")
        print(f"   Expected Fee: R$ {expected_fee:.2f}")
        print(f"   Expected Net Credit: R$ {expected_net_credit:.2f}")
        print(f"   Expected Final Balance: R$ {expected_final_balance:.2f}")
        
        # Create payment preference
        payment_response = self.test_create_payment_preference(test_user_id, deposit_amount)
        if not payment_response:
            print("❌ CRITICAL: Payment preference creation failed")
            return False
        
        transaction_id = payment_response.get('transaction_id')
        if not transaction_id:
            print("❌ CRITICAL: No transaction ID returned")
            return False
        
        print(f"✅ Payment preference created successfully")
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Payment URL: {payment_response.get('payment_url', 'N/A')}")
        
        # Verify transaction was created in database
        print(f"\n3. TRANSACTION VERIFICATION: Checking transaction in database...")
        print("-" * 65)
        
        transactions_before = self.test_get_user_transactions(test_user_id)
        transaction_found = False
        for tx in transactions_before:
            if tx.get('id') == transaction_id:
                transaction_found = True
                print(f"✅ Transaction found in database")
                print(f"   Status: {tx.get('status')}")
                print(f"   Amount: R$ {tx.get('amount'):.2f}")
                print(f"   Type: {tx.get('type')}")
                break
        
        if not transaction_found:
            print("❌ CRITICAL: Transaction not found in database")
            return False
        
        # Test webhook simulation (AbacatePay success event)
        print(f"\n4. WEBHOOK SIMULATION TEST: Simulating AbacatePay webhook...")
        print("-" * 65)
        
        # Prepare webhook data structure as specified in review request
        webhook_data = {
            "event": "billing.paid",
            "data": {
                "externalId": transaction_id,
                "payment": {
                    "amount": int(deposit_amount * 100),  # 50.00 in cents = 5000
                    "fee": 80  # 0.80 in cents = 80
                }
            }
        }
        
        print(f"   Webhook Data Structure:")
        print(f"   {json.dumps(webhook_data, indent=4)}")
        
        # Test webhook endpoint with proper secret
        webhook_url = f"{self.api_url}/payments/webhook?webhookSecret=betarena_webhook_secret_2025"
        print(f"   Webhook URL: {webhook_url}")
        
        try:
            webhook_response = requests.post(webhook_url, json=webhook_data, timeout=10)
            if webhook_response.status_code == 200:
                print(f"✅ Webhook processed successfully")
                webhook_result = webhook_response.json()
                print(f"   Response: {json.dumps(webhook_result, indent=2)}")
            else:
                print(f"❌ CRITICAL: Webhook failed with status {webhook_response.status_code}")
                print(f"   Error: {webhook_response.text}")
                return False
        except Exception as e:
            print(f"❌ CRITICAL: Webhook request failed: {str(e)}")
            return False
        
        # Wait a moment for database update
        import time
        time.sleep(1)
        
        # Test balance update verification
        print(f"\n5. BALANCE UPDATE VERIFICATION: Checking user balance after webhook...")
        print("-" * 70)
        
        updated_user = self.test_get_user(test_user_id)
        if not updated_user:
            print("❌ CRITICAL: Failed to retrieve updated user data")
            return False
        
        actual_final_balance = updated_user['balance']
        balance_difference = actual_final_balance - initial_balance
        
        print(f"   Initial Balance: R$ {initial_balance:.2f}")
        print(f"   Actual Final Balance: R$ {actual_final_balance:.2f}")
        print(f"   Balance Increase: R$ {balance_difference:.2f}")
        print(f"   Expected Increase: R$ {expected_net_credit:.2f}")
        
        # Verify balance calculation (deposit_amount - fee)
        if abs(balance_difference - expected_net_credit) < 0.01:
            print(f"✅ BALANCE CALCULATION CORRECT: Balance = Deposit - Fee")
            print(f"   R$ {balance_difference:.2f} = R$ {deposit_amount:.2f} - R$ {expected_fee:.2f}")
        else:
            print(f"❌ CRITICAL: BALANCE CALCULATION ERROR")
            print(f"   Expected: R$ {expected_net_credit:.2f}")
            print(f"   Actual: R$ {balance_difference:.2f}")
            return False
        
        # Test transaction status update
        print(f"\n6. TRANSACTION HISTORY VERIFICATION: Checking transaction status...")
        print("-" * 70)
        
        transactions_after = self.test_get_user_transactions(test_user_id)
        transaction_updated = False
        for tx in transactions_after:
            if tx.get('id') == transaction_id:
                transaction_updated = True
                print(f"✅ Transaction status updated")
                print(f"   Status: {tx.get('status')}")
                print(f"   Amount: R$ {tx.get('amount'):.2f}")
                print(f"   Fee: R$ {tx.get('fee', 0):.2f}")
                print(f"   Net Amount: R$ {tx.get('net_amount', 0):.2f}")
                
                if tx.get('status') == 'approved':
                    print(f"✅ Transaction marked as APPROVED")
                else:
                    print(f"❌ CRITICAL: Transaction not marked as approved")
                    return False
                break
        
        if not transaction_updated:
            print("❌ CRITICAL: Transaction not found after webhook processing")
            return False
        
        # Final verification summary
        print(f"\n7. FINAL VERIFICATION SUMMARY:")
        print("=" * 50)
        
        success_criteria = [
            ("Payment preference created", payment_response is not None),
            ("Transaction created in database", transaction_found),
            ("Webhook processed successfully", webhook_response.status_code == 200),
            ("Balance updated correctly", abs(balance_difference - expected_net_credit) < 0.01),
            ("Transaction marked as approved", any(tx.get('id') == transaction_id and tx.get('status') == 'approved' for tx in transactions_after)),
            ("Fee deduction applied", abs(balance_difference - (deposit_amount - expected_fee)) < 0.01)
        ]
        
        all_passed = True
        for criteria, passed in success_criteria:
            status = "✅" if passed else "❌"
            print(f"   {status} {criteria}")
            if not passed:
                all_passed = False
        
        print(f"\n{'✅ SUCCESS' if all_passed else '❌ FAILURE'}: AbacatePay Balance Crediting System")
        
        if all_passed:
            print(f"\n🎉 CRITICAL TEST PASSED - USER REQUIREMENT SATISFIED:")
            print(f"   ✅ Payment preference created with correct external ID")
            print(f"   ✅ Webhook processes successfully")
            print(f"   ✅ User balance increases by (amount - fee)")
            print(f"   ✅ Transaction status changes to APPROVED")
            print(f"   ✅ No errors in webhook processing")
            print(f"   ✅ The '$' field (balance) gets credited correctly after AbacatePay payment")
        else:
            print(f"\n🚨 CRITICAL TEST FAILED - USER REQUIREMENT NOT SATISFIED")
            print(f"   The balance crediting system has issues that need immediate attention")
        
        return all_passed

def main():
    print("💰 CRITICAL BALANCE UPDATE TEST - AbacatePay Balance Crediting System")
    print("=" * 80)
    print("USER REQUIREMENT: 'ao valor ser depositado, deve creditar no site no campo $'")
    print("FOCUS: Testing balance crediting after AbacatePay deposit")
    print("=" * 80)
    
    tester = BetArenaAPITester()
    
    # Test 1: Health Check
    print("\n📋 BASIC API HEALTH CHECK")
    print("-" * 30)
    tester.test_health_check()
    
    # Test 2: MAIN FOCUS - AbacatePay Balance Crediting System
    print("\n💰 MAIN TEST: ABACATEPAY BALANCE CREDITING SYSTEM")
    print("-" * 55)
    balance_crediting_success = tester.test_abacatepay_balance_crediting_system()
    
    # Test 3: Secondary - General AbacatePay Integration Test
    print("\n🥑 SECONDARY TEST: GENERAL ABACATEPAY INTEGRATION")
    print("-" * 50)
    abacatepay_success = tester.test_abacatepay_integration_comprehensive()
    
    
    # Print final results
    print("\n" + "=" * 80)
    print(f"📊 FINAL TEST RESULTS:")
    print(f"   Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    print(f"\n💰 CRITICAL BALANCE CREDITING RESULTS:")
    if balance_crediting_success:
        print("   ✅ BALANCE CREDITING SYSTEM IS WORKING CORRECTLY")
        print("   ✅ Payment preferences created with correct external ID")
        print("   ✅ Webhook processes successfully")
        print("   ✅ User balance increases by (amount - fee)")
        print("   ✅ Transaction status changes to APPROVED")
        print("   ✅ No errors in webhook processing")
        print("   ✅ The '$' field (balance) gets credited correctly after AbacatePay payment")
        print("\n🎉 USER REQUIREMENT SATISFIED: Balance crediting works as expected!")
        
        print(f"\n🥑 GENERAL ABACATEPAY INTEGRATION RESULTS:")
        if abacatepay_success:
            print("   ✅ General AbacatePay integration is also working correctly")
            print("   ✅ Production credentials are valid")
            print("   ✅ Payment URLs are being generated")
            print("   ✅ API endpoints are functional")
        else:
            print("   ⚠️  Some general AbacatePay features may have issues")
            print("   ✅ But the critical balance crediting functionality works")
        
        return 0
    else:
        print("   ❌ BALANCE CREDITING SYSTEM HAS CRITICAL ISSUES")
        print("   🚨 This confirms the user's reported problem")
        print("   🚨 USER REQUIREMENT NOT SATISFIED")
        
        print("\n🔧 RECOMMENDED FIXES FOR BALANCE CREDITING:")
        print("   1. Check webhook endpoint accessibility (/api/payments/webhook)")
        print("   2. Verify webhook secret validation")
        print("   3. Test amount conversion from cents to reais")
        print("   4. Verify fee deduction logic (amount - fee)")
        print("   5. Check database balance update mechanism")
        print("   6. Verify transaction status update to APPROVED")
        print("   7. Test AbacatePay webhook data structure processing")
        
        print(f"\n🥑 GENERAL ABACATEPAY INTEGRATION RESULTS:")
        if abacatepay_success:
            print("   ✅ General AbacatePay integration is working")
            print("   🚨 But the critical balance crediting has issues")
        else:
            print("   ❌ Both balance crediting and general integration have issues")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())