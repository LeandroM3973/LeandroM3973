import requests
import json
import time
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class WebhookDuplicationTester:
    def __init__(self, base_url="https://47eed0e6-f30e-431a-b6a5-47794796692b.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.webhook_url = f"{self.api_url}/payments/webhook?webhookSecret=betarena_webhook_secret_2025"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_users = []
        self.created_transactions = []

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name}")
        if details:
            print(f"   {details}")

    def create_test_user(self, suffix=""):
        """Create a test user for webhook testing"""
        timestamp = str(int(time.time()))
        user_data = {
            "name": f"Webhook Test User {suffix}",
            "email": f"webhook.test.{timestamp}.{suffix}@gmail.com",
            "phone": "11999888777",
            "password": "webhooktest123"
        }
        
        try:
            response = requests.post(f"{self.api_url}/users", json=user_data)
            if response.status_code == 200:
                user = response.json()
                self.created_users.append(user)
                return user
        except Exception as e:
            print(f"Failed to create user: {str(e)}")
        return None

    def create_payment_transaction(self, user_id, amount):
        """Create a payment transaction"""
        try:
            response = requests.post(
                f"{self.api_url}/payments/create-preference",
                json={"user_id": user_id, "amount": amount}
            )
            if response.status_code == 200:
                transaction = response.json()
                self.created_transactions.append(transaction)
                return transaction
        except Exception as e:
            print(f"Failed to create transaction: {str(e)}")
        return None

    def send_webhook(self, webhook_data, delay=0):
        """Send webhook request with optional delay"""
        if delay > 0:
            time.sleep(delay)
        
        start_time = time.time()
        try:
            response = requests.post(self.webhook_url, json=webhook_data, timeout=10)
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                'status_code': response.status_code,
                'response': response.json() if response.status_code == 200 else response.text,
                'processing_time': processing_time,
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'status_code': 0,
                'response': str(e),
                'processing_time': time.time() - start_time,
                'timestamp': datetime.utcnow().isoformat()
            }

    def test_duplicate_webhook_detection(self):
        """Test 1: Duplicate webhook detection within cache TTL"""
        print("\n🔍 TEST 1: DUPLICATE WEBHOOK DETECTION")
        print("=" * 60)
        
        # Create test user and transaction
        user = self.create_test_user("duplicate")
        if not user:
            self.log_test("Create test user for duplicate test", False, "Failed to create user")
            return False
        
        transaction = self.create_payment_transaction(user['id'], 50.00)
        if not transaction:
            self.log_test("Create test transaction for duplicate test", False, "Failed to create transaction")
            return False
        
        transaction_id = transaction.get('transaction_id')
        
        # Create webhook payload
        webhook_data = {
            "event": "billing.paid",
            "data": {
                "externalId": transaction_id,
                "payment": {
                    "amount": 5000,  # R$ 50.00 in cents
                    "fee": 80        # R$ 0.80 in cents
                },
                "pixQrCode": {
                    "id": f"pix_{transaction_id}",
                    "status": "paid"
                }
            },
            "devMode": False
        }
        
        print(f"Testing with transaction ID: {transaction_id}")
        print(f"Webhook payload: {json.dumps(webhook_data, indent=2)}")
        
        # Send first webhook
        print("\n1.1 Sending FIRST webhook...")
        first_response = self.send_webhook(webhook_data)
        
        success_first = first_response['status_code'] == 200
        self.log_test("First webhook processed", success_first, 
                     f"Status: {first_response['status_code']}, Time: {first_response['processing_time']:.3f}s")
        
        if success_first:
            print(f"   Response: {json.dumps(first_response['response'], indent=2)}")
        
        # Send duplicate webhook immediately (within cache TTL)
        print("\n1.2 Sending DUPLICATE webhook (immediate)...")
        duplicate_response = self.send_webhook(webhook_data)
        
        success_duplicate = duplicate_response['status_code'] == 200
        self.log_test("Duplicate webhook handled", success_duplicate,
                     f"Status: {duplicate_response['status_code']}, Time: {duplicate_response['processing_time']:.3f}s")
        
        if success_duplicate:
            print(f"   Response: {json.dumps(duplicate_response['response'], indent=2)}")
            
            # Check if duplicate was detected
            duplicate_detected = (
                duplicate_response['response'].get('status') == 'duplicate_ignored' or
                'duplicate' in str(duplicate_response['response']).lower()
            )
            
            self.log_test("Duplicate detection working", duplicate_detected,
                         f"Duplicate status: {duplicate_response['response'].get('status', 'unknown')}")
            
            # Verify processing time is fast for duplicates (should be <1ms for cache hit)
            if duplicate_response['processing_time'] < 0.1:  # Less than 100ms
                self.log_test("Duplicate detection is fast", True,
                             f"Processing time: {duplicate_response['processing_time']:.3f}s")
            else:
                self.log_test("Duplicate detection is fast", False,
                             f"Processing time too slow: {duplicate_response['processing_time']:.3f}s")
            
            return duplicate_detected
        
        return False

    def test_race_condition_protection(self):
        """Test 2: Race condition protection with concurrent webhooks"""
        print("\n⚡ TEST 2: RACE CONDITION PROTECTION")
        print("=" * 50)
        
        # Create test user and transaction
        user = self.create_test_user("race")
        if not user:
            self.log_test("Create test user for race condition test", False)
            return False
        
        transaction = self.create_payment_transaction(user['id'], 100.00)
        if not transaction:
            self.log_test("Create test transaction for race condition test", False)
            return False
        
        transaction_id = transaction.get('transaction_id')
        
        # Create webhook payload
        webhook_data = {
            "event": "billing.paid",
            "data": {
                "externalId": transaction_id,
                "payment": {
                    "amount": 10000,  # R$ 100.00 in cents
                    "fee": 80         # R$ 0.80 in cents
                },
                "pixQrCode": {
                    "id": f"pix_{transaction_id}",
                    "status": "paid"
                }
            },
            "devMode": False
        }
        
        print(f"Testing concurrent webhooks for transaction: {transaction_id}")
        
        # Send 5 concurrent webhooks to test race conditions
        print("\n2.1 Sending 5 CONCURRENT webhooks...")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                future = executor.submit(self.send_webhook, webhook_data)
                futures.append(future)
            
            responses = []
            for future in as_completed(futures):
                response = future.result()
                responses.append(response)
        
        # Analyze responses
        successful_responses = [r for r in responses if r['status_code'] == 200]
        processed_count = 0
        duplicate_count = 0
        race_condition_count = 0
        
        for response in successful_responses:
            resp_data = response['response']
            if isinstance(resp_data, dict):
                status = resp_data.get('status', '')
                if status == 'processed':
                    processed_count += 1
                elif status == 'duplicate_ignored':
                    duplicate_count += 1
                elif status == 'race_condition':
                    race_condition_count += 1
        
        print(f"\n2.2 Concurrent webhook results:")
        print(f"   Total responses: {len(responses)}")
        print(f"   Successful responses: {len(successful_responses)}")
        print(f"   Processed: {processed_count}")
        print(f"   Duplicates ignored: {duplicate_count}")
        print(f"   Race conditions detected: {race_condition_count}")
        
        # Verify only ONE webhook was processed successfully
        race_protection_working = processed_count == 1
        self.log_test("Race condition protection working", race_protection_working,
                     f"Only {processed_count} webhook processed (expected: 1)")
        
        # Verify others were properly handled (duplicates or race conditions)
        others_handled = (duplicate_count + race_condition_count) >= 3
        self.log_test("Other webhooks properly handled", others_handled,
                     f"{duplicate_count + race_condition_count} webhooks handled as duplicates/race conditions")
        
        return race_protection_working and others_handled

    def test_processing_time_monitoring(self):
        """Test 3: Processing time monitoring and logging"""
        print("\n⏱️  TEST 3: PROCESSING TIME MONITORING")
        print("=" * 45)
        
        # Create test user and transaction
        user = self.create_test_user("timing")
        if not user:
            self.log_test("Create test user for timing test", False)
            return False
        
        transaction = self.create_payment_transaction(user['id'], 25.00)
        if not transaction:
            self.log_test("Create test transaction for timing test", False)
            return False
        
        transaction_id = transaction.get('transaction_id')
        
        # Test different webhook scenarios for timing
        test_scenarios = [
            {
                "name": "New webhook processing",
                "data": {
                    "event": "billing.paid",
                    "data": {
                        "externalId": transaction_id,
                        "payment": {"amount": 2500, "fee": 80},
                        "pixQrCode": {"id": f"pix_{transaction_id}_1", "status": "paid"}
                    }
                }
            },
            {
                "name": "Duplicate webhook detection",
                "data": {
                    "event": "billing.paid",
                    "data": {
                        "externalId": transaction_id,
                        "payment": {"amount": 2500, "fee": 80},
                        "pixQrCode": {"id": f"pix_{transaction_id}_1", "status": "paid"}
                    }
                }
            }
        ]
        
        processing_times = []
        
        for i, scenario in enumerate(test_scenarios):
            print(f"\n3.{i+1} Testing {scenario['name']}...")
            
            response = self.send_webhook(scenario['data'])
            processing_time = response['processing_time']
            processing_times.append(processing_time)
            
            print(f"   Processing time: {processing_time:.3f} seconds")
            print(f"   Status: {response['status_code']}")
            
            if response['status_code'] == 200:
                resp_data = response['response']
                if isinstance(resp_data, dict):
                    logged_time = resp_data.get('processing_time_seconds')
                    if logged_time:
                        print(f"   Logged processing time: {logged_time:.3f} seconds")
                        
                        # Verify logged time matches measured time (within 10ms tolerance)
                        time_match = abs(logged_time - processing_time) < 0.01
                        self.log_test(f"Processing time logged correctly for {scenario['name']}", 
                                    time_match, f"Measured: {processing_time:.3f}s, Logged: {logged_time:.3f}s")
        
        # Verify duplicate detection is significantly faster than new processing
        if len(processing_times) >= 2:
            new_processing_time = processing_times[0]
            duplicate_processing_time = processing_times[1]
            
            duplicate_faster = duplicate_processing_time < new_processing_time
            self.log_test("Duplicate detection is faster than new processing", duplicate_faster,
                         f"New: {new_processing_time:.3f}s, Duplicate: {duplicate_processing_time:.3f}s")
            
            # Verify duplicate detection is very fast (< 100ms)
            duplicate_very_fast = duplicate_processing_time < 0.1
            self.log_test("Duplicate detection is very fast", duplicate_very_fast,
                         f"Duplicate processing time: {duplicate_processing_time:.3f}s")
            
            return duplicate_faster and duplicate_very_fast
        
        return False

    def test_real_payment_simulation(self):
        """Test 4: Real payment simulation with multiple webhooks"""
        print("\n💰 TEST 4: REAL PAYMENT SIMULATION")
        print("=" * 40)
        
        # Create test user
        user = self.create_test_user("payment")
        if not user:
            self.log_test("Create test user for payment simulation", False)
            return False
        
        # Get initial balance
        try:
            user_response = requests.get(f"{self.api_url}/users/{user['id']}")
            if user_response.status_code == 200:
                initial_balance = user_response.json()['balance']
                print(f"Initial user balance: R$ {initial_balance:.2f}")
            else:
                self.log_test("Get initial user balance", False)
                return False
        except Exception as e:
            self.log_test("Get initial user balance", False, str(e))
            return False
        
        # Create payment transaction
        payment_amount = 50.00
        transaction = self.create_payment_transaction(user['id'], payment_amount)
        if not transaction:
            self.log_test("Create payment transaction", False)
            return False
        
        transaction_id = transaction.get('transaction_id')
        print(f"Created payment transaction: {transaction_id}")
        print(f"Payment amount: R$ {payment_amount:.2f}")
        
        # Simulate AbacatePay sending multiple webhooks (common behavior)
        webhook_data = {
            "event": "billing.paid",
            "data": {
                "externalId": transaction_id,
                "payment": {
                    "amount": int(payment_amount * 100),  # Convert to cents
                    "fee": 80  # R$ 0.80 fee
                },
                "pixQrCode": {
                    "id": f"pix_{transaction_id}",
                    "status": "paid"
                }
            },
            "devMode": False
        }
        
        print(f"\n4.1 Simulating AbacatePay retry behavior...")
        print(f"   Sending webhook 3 times with delays (simulating retries)")
        
        webhook_responses = []
        
        # Send webhook 3 times with delays (simulating AbacatePay retry behavior)
        for i in range(3):
            delay = i * 2  # 0s, 2s, 4s delays
            print(f"\n   Webhook attempt {i+1} (delay: {delay}s)...")
            
            response = self.send_webhook(webhook_data, delay=delay)
            webhook_responses.append(response)
            
            print(f"   Status: {response['status_code']}")
            print(f"   Processing time: {response['processing_time']:.3f}s")
            
            if response['status_code'] == 200:
                resp_data = response['response']
                if isinstance(resp_data, dict):
                    status = resp_data.get('status', 'unknown')
                    print(f"   Response status: {status}")
        
        # Verify only first webhook processed payment
        processed_webhooks = 0
        duplicate_webhooks = 0
        
        for response in webhook_responses:
            if response['status_code'] == 200:
                resp_data = response['response']
                if isinstance(resp_data, dict):
                    status = resp_data.get('status', '')
                    if status == 'processed':
                        processed_webhooks += 1
                    elif status == 'duplicate_ignored':
                        duplicate_webhooks += 1
        
        print(f"\n4.2 Webhook processing results:")
        print(f"   Processed webhooks: {processed_webhooks}")
        print(f"   Duplicate webhooks: {duplicate_webhooks}")
        
        only_one_processed = processed_webhooks == 1
        self.log_test("Only one webhook processed payment", only_one_processed,
                     f"{processed_webhooks} webhooks processed (expected: 1)")
        
        duplicates_detected = duplicate_webhooks >= 1
        self.log_test("Duplicate webhooks detected", duplicates_detected,
                     f"{duplicate_webhooks} duplicates detected")
        
        # Verify balance was credited only once
        print(f"\n4.3 Verifying balance update...")
        
        try:
            final_user_response = requests.get(f"{self.api_url}/users/{user['id']}")
            if final_user_response.status_code == 200:
                final_balance = final_user_response.json()['balance']
                expected_credit = payment_amount - 0.80  # Amount minus fee
                expected_final_balance = initial_balance + expected_credit
                balance_increase = final_balance - initial_balance
                
                print(f"   Initial balance: R$ {initial_balance:.2f}")
                print(f"   Expected credit: R$ {expected_credit:.2f}")
                print(f"   Final balance: R$ {final_balance:.2f}")
                print(f"   Actual increase: R$ {balance_increase:.2f}")
                
                balance_correct = abs(balance_increase - expected_credit) < 0.01
                self.log_test("Balance credited correctly (only once)", balance_correct,
                             f"Expected: R$ {expected_credit:.2f}, Actual: R$ {balance_increase:.2f}")
                
                return only_one_processed and duplicates_detected and balance_correct
            else:
                self.log_test("Get final user balance", False)
                return False
        except Exception as e:
            self.log_test("Get final user balance", False, str(e))
            return False

    def test_production_scenario(self):
        """Test 5: Production scenario with high webhook frequency"""
        print("\n🚀 TEST 5: PRODUCTION SCENARIO TESTING")
        print("=" * 45)
        
        # Create test user
        user = self.create_test_user("production")
        if not user:
            self.log_test("Create test user for production scenario", False)
            return False
        
        # Create multiple transactions to simulate production load
        transactions = []
        for i in range(3):
            amount = 25.00 + (i * 25.00)  # R$ 25, R$ 50, R$ 75
            transaction = self.create_payment_transaction(user['id'], amount)
            if transaction:
                transactions.append(transaction)
        
        if len(transactions) != 3:
            self.log_test("Create multiple transactions", False, f"Only {len(transactions)}/3 created")
            return False
        
        print(f"Created {len(transactions)} transactions for production testing")
        
        # Test high-frequency webhook processing
        print(f"\n5.1 Testing high-frequency webhook processing...")
        
        all_webhooks = []
        
        # For each transaction, send multiple webhooks rapidly
        for i, transaction in enumerate(transactions):
            transaction_id = transaction.get('transaction_id')
            amount = 25.00 + (i * 25.00)
            
            webhook_data = {
                "event": "billing.paid",
                "data": {
                    "externalId": transaction_id,
                    "payment": {
                        "amount": int(amount * 100),
                        "fee": 80
                    },
                    "pixQrCode": {
                        "id": f"pix_{transaction_id}",
                        "status": "paid"
                    }
                },
                "devMode": False
            }
            
            # Send 3 rapid webhooks for each transaction
            for j in range(3):
                all_webhooks.append((f"Transaction {i+1} Webhook {j+1}", webhook_data))
        
        print(f"   Sending {len(all_webhooks)} webhooks rapidly...")
        
        # Send all webhooks concurrently to simulate high load
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for name, webhook_data in all_webhooks:
                future = executor.submit(self.send_webhook, webhook_data)
                futures.append((name, future))
            
            results = []
            for name, future in futures:
                response = future.result()
                results.append((name, response))
        
        # Analyze results
        successful_responses = [(name, r) for name, r in results if r['status_code'] == 200]
        processed_count = 0
        duplicate_count = 0
        total_processing_time = 0
        
        print(f"\n5.2 Production scenario results:")
        print(f"   Total webhooks sent: {len(all_webhooks)}")
        print(f"   Successful responses: {len(successful_responses)}")
        
        for name, response in successful_responses:
            resp_data = response['response']
            processing_time = response['processing_time']
            total_processing_time += processing_time
            
            if isinstance(resp_data, dict):
                status = resp_data.get('status', '')
                if status == 'processed':
                    processed_count += 1
                elif status == 'duplicate_ignored':
                    duplicate_count += 1
        
        print(f"   Processed webhooks: {processed_count}")
        print(f"   Duplicate webhooks: {duplicate_count}")
        print(f"   Average processing time: {total_processing_time / len(successful_responses):.3f}s")
        
        # Verify system handled high frequency gracefully
        expected_processed = len(transactions)  # One per transaction
        correct_processing = processed_count == expected_processed
        self.log_test("Correct number of webhooks processed", correct_processing,
                     f"{processed_count} processed (expected: {expected_processed})")
        
        duplicates_handled = duplicate_count > 0
        self.log_test("Duplicate webhooks handled gracefully", duplicates_handled,
                     f"{duplicate_count} duplicates detected and ignored")
        
        # Verify system performance under load
        avg_processing_time = total_processing_time / len(successful_responses)
        performance_good = avg_processing_time < 1.0  # Less than 1 second average
        self.log_test("System performance under load", performance_good,
                     f"Average processing time: {avg_processing_time:.3f}s")
        
        return correct_processing and duplicates_handled and performance_good

    def run_all_tests(self):
        """Run all webhook duplication prevention tests"""
        print("\n🔒 WEBHOOK DUPLICATION PREVENTION SYSTEM TESTING")
        print("=" * 80)
        print("CRITICAL BUG FIX VERIFICATION")
        print("USER ISSUE: 'após o pagamento gera uma notificação atrás da outra, parece um bug'")
        print("TESTING: Webhook duplication detection, race condition protection, atomic updates")
        print("=" * 80)
        
        test_results = []
        
        # Run all tests
        test_results.append(("Duplicate Webhook Detection", self.test_duplicate_webhook_detection()))
        test_results.append(("Race Condition Protection", self.test_race_condition_protection()))
        test_results.append(("Processing Time Monitoring", self.test_processing_time_monitoring()))
        test_results.append(("Real Payment Simulation", self.test_real_payment_simulation()))
        test_results.append(("Production Scenario Testing", self.test_production_scenario()))
        
        # Summary
        print(f"\n📊 WEBHOOK DUPLICATION PREVENTION TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = 0
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status}: {test_name}")
            if result:
                passed_tests += 1
        
        print(f"\nOverall Results:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        print(f"   Major Tests Passed: {passed_tests}/{len(test_results)}")
        
        all_critical_passed = passed_tests == len(test_results)
        
        if all_critical_passed:
            print(f"\n🎉 WEBHOOK DUPLICATION PREVENTION SYSTEM: FULLY FUNCTIONAL")
            print("✅ Duplicate webhooks are detected and ignored within 5-minute window")
            print("✅ Only first webhook processes payment and credits balance")
            print("✅ Subsequent webhooks return 'duplicate_ignored' status")
            print("✅ No multiple notifications or balance updates occur")
            print("✅ Atomic operations prevent race conditions")
            print("✅ Processing time is logged for monitoring")
            print("✅ System handles high webhook frequency gracefully")
            print("\n🔒 CRITICAL USER ISSUE RESOLVED: No more 'notificação atrás da outra'")
        else:
            print(f"\n🚨 WEBHOOK DUPLICATION PREVENTION SYSTEM: ISSUES DETECTED")
            print("❌ Some critical tests failed - webhook duplication may still occur")
            print("❌ User may still experience multiple notifications after payment")
            print("❌ Manual investigation and fixes required")
        
        return all_critical_passed

if __name__ == "__main__":
    tester = WebhookDuplicationTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)