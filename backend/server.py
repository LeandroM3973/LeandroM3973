from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta, timedelta
from enum import Enum
from abacatepay import AbacatePay

import json
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# AbacatePay Configuration
abacate_api_token = os.environ.get('ABACATEPAY_API_TOKEN')
abacate_webhook_secret = os.environ.get('ABACATEPAY_WEBHOOK_SECRET')
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Validate AbacatePay configuration
def validate_abacatepay_credentials():
    if not abacate_api_token or not abacate_webhook_secret:
        print("⚠️  WARNING: AbacatePay credentials not configured - using demo mode")
        return False
    
    if abacate_api_token == "your_abacatepay_api_token_here":
        print("⚠️  WARNING: Using placeholder AbacatePay credentials - demo mode enabled")
        return False
    
    if len(abacate_api_token) < 10:
        print("❌ ERROR: Invalid AbacatePay API token format")
        return False
    
    print(f"🥑 AbacatePay: Configuration validated successfully")
    print(f"🌐 Frontend URL: {frontend_url}")
    return True

# Initialize AbacatePay with validation
abacate_valid = validate_abacatepay_credentials()
abacatepay_client = AbacatePay(abacate_api_token) if abacate_api_token and abacate_valid else None

# Legacy variables for backward compatibility (will be removed)
mp_valid = abacate_valid
mp = abacatepay_client
mp_access_token = abacate_api_token

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class BetStatus(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class EventType(str, Enum):
    SPORTS = "sports"
    STOCKS = "stocks"
    CUSTOM = "custom"

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BET_DEBIT = "bet_debit"
    BET_CREDIT = "bet_credit"
    PLATFORM_FEE = "platform_fee"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone: str
    password_hash: str  # Added password hash field
    is_admin: bool = False  # Added admin flag
    balance: float = 0.0  # Changed to real currency (BRL)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    name: str
    email: str
    phone: str
    password: str  # Added password field

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    balance: float
    created_at: datetime

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    amount: float
    type: TransactionType
    status: TransactionStatus
    payment_id: Optional[str] = None
    mp_payment_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Bet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invite_code: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])  # Short invite code
    event_title: str
    event_type: EventType
    event_description: str
    amount: float  # Changed to float for real currency
    creator_id: str
    creator_name: str
    opponent_id: Optional[str] = None
    opponent_name: Optional[str] = None
    winner_id: Optional[str] = None
    winner_name: Optional[str] = None
    status: BetStatus = BetStatus.WAITING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(minutes=20))  # 20 min timeout
    # New fields for platform fee tracking
    platform_fee: Optional[float] = None
    winner_payout: Optional[float] = None
    total_pot: Optional[float] = None

class BetCreate(BaseModel):
    event_title: str
    event_type: EventType
    event_description: str
    amount: float
    creator_id: str

class JoinBet(BaseModel):
    user_id: str

class DeclareWinner(BaseModel):
    winner_id: str

class DepositRequest(BaseModel):
    user_id: str
    amount: float

class WithdrawRequest(BaseModel):
    user_id: str
    amount: float

class CreatePaymentRequest(BaseModel):
    user_id: str
    amount: float

# User Routes
# Password hashing utilities
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# User Routes
@api_router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    # Check if user already exists by email
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Validate password strength
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    
    # Hash the password
    password_hash = hash_password(user_data.password)
    
    # Create user with hashed password
    user_dict = user_data.dict()
    user_dict.pop('password')  # Remove plain password
    user_dict['password_hash'] = password_hash
    
    user = User(**user_dict)
    await db.users.insert_one(user.dict())
    print(f"New user created for email: {user_data.email}")
    
    # Return user data without password hash
    return UserResponse(**user.dict())

@api_router.post("/users/login", response_model=UserResponse)
async def login_user(login_data: UserLogin):
    """Login user with email and password"""
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    print(f"User logged in: {login_data.email}")
    return UserResponse(**user)

@api_router.post("/users/check-email")
async def check_email_exists(email: str):
    """Check if email exists in system"""
    user = await db.users.find_one({"email": email})
    return {"exists": user is not None}

@api_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user)

@api_router.get("/users", response_model=List[UserResponse])
async def get_all_users():
    users = await db.users.find().to_list(1000)
    return [UserResponse(**user) for user in users]

# Payment Routes
@api_router.post("/payments/create-preference")
async def create_payment_preference(request: CreatePaymentRequest):
    """Create payment preference using AbacatePay"""
    
    if not abacatepay_client or not abacate_valid:
        # Return demo mode when AbacatePay is not properly configured
        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            type=TransactionType.DEPOSIT,
            amount=request.amount,
            status=TransactionStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        await db.transactions.insert_one(transaction.dict())
        
        return {
            "demo_mode": True,
            "transaction_id": transaction.id,
            "message": "Demo mode - AbacatePay not configured. Use 'OK' to simulate approval."
        }
    
    # Get user details for payment
    user = await db.users.find_one({"id": request.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create transaction record
    transaction = Transaction(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        type=TransactionType.DEPOSIT,
        amount=request.amount,
        status=TransactionStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    await db.transactions.insert_one(transaction.dict())
    
    try:
        # Create product for AbacatePay
        product = {
            "externalId": transaction.id,
            "name": f"Depósito BetArena - {user['name']}",
            "description": f"Depósito para conta de apostas - {user['email']}",
            "quantity": 1,
            "price": int(request.amount * 100)  # Convert to cents
        }
        
        # Create billing with AbacatePay
        billing_data = {
            "products": [product],
            "return_url": f"{frontend_url}/payment-success",
            "completion_url": f"{frontend_url}/payment-success", 
            "customer": {
                "name": user["name"],
                "email": user["email"],
                "cellphone": user["phone"],
                "taxId": "11144477735"  # Valid test CPF for AbacatePay
            }
        }
        
        billing_response = abacatepay_client.billing.create(data=billing_data)
        
        # Update transaction with payment ID
        await db.transactions.update_one(
            {"id": transaction.id},
            {"$set": {
                "payment_id": billing_response.id,
                "external_reference": billing_response.id
            }}
        )
        
        return {
            "preference_id": billing_response.id,
            "init_point": billing_response.url,
            "sandbox_init_point": billing_response.url,  # AbacatePay uses same URL
            "transaction_id": transaction.id,
            "real_mp": False,  # Changed to indicate AbacatePay usage
            "abacatepay": True,
            "test_mode": billing_response.dev_mode,
            "payment_url": billing_response.url,
            "amount": billing_response.amount / 100,  # Convert back to reais
            "fee": 0.80,  # AbacatePay fixed fee
            "status": billing_response.status,
            "message": f"Pagamento via AbacatePay configurado com sucesso! Taxa: R$ 0,80"
        }
    
    except Exception as e:
        logging.error(f"AbacatePay payment creation error: {str(e)}")
        print(f"❌ AbacatePay Error Details: {str(e)}")
        
        # Delete failed transaction
        await db.transactions.delete_one({"id": transaction.id})
        
        raise HTTPException(status_code=500, detail=f"Erro ao criar pagamento via AbacatePay: {str(e)}")

@api_router.post("/payments/simulate-approval/{transaction_id}")
async def simulate_payment_approval(transaction_id: str):
    """Simulate payment approval for demo purposes"""
    transaction = await db.transactions.find_one({"id": transaction_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction["status"] == TransactionStatus.APPROVED:
        return {"message": "Payment already approved", "status": "approved"}
    
    # Update transaction status to approved
    await db.transactions.update_one(
        {"id": transaction_id},
        {
            "$set": {
                "status": TransactionStatus.APPROVED,
                "mp_payment_id": f"demo_payment_{transaction_id}",
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Add balance to user
    await db.users.update_one(
        {"id": transaction["user_id"]},
        {"$inc": {"balance": transaction["amount"]}}
    )
    
    return {
        "message": "Payment simulated successfully!",
        "status": "approved",
        "amount": transaction["amount"],
        "transaction_id": transaction_id
    }

@api_router.post("/payments/webhook")
async def webhook_abacatepay(request: Request):
    """AbacatePay webhook endpoint"""
    try:
        # Validate webhook secret from query parameters
        webhook_secret = request.query_params.get('webhookSecret')
        if not webhook_secret or webhook_secret != abacate_webhook_secret:
            print(f"❌ Invalid AbacatePay webhook secret")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
        
        # Parse webhook payload
        webhook_data = await request.json()
        event_type = webhook_data.get('event')
        
        print(f"🥑 AbacatePay Webhook received: {event_type}")
        
        if event_type == 'billing.paid':
            await process_abacatepay_payment_success(webhook_data)
        elif event_type == 'billing.failed':
            await process_abacatepay_payment_failure(webhook_data)
        elif event_type == 'billing.cancelled':
            await process_abacatepay_payment_cancellation(webhook_data)
        else:
            print(f"⚠️ Unknown AbacatePay webhook event: {event_type}")
        
        return {"received": True, "event": event_type}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ AbacatePay Webhook Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Webhook processing error: {str(e)}")

async def process_abacatepay_payment_success(webhook_data: Dict[str, Any]):
    """Process successful AbacatePay payment"""
    try:
        payment_data = webhook_data.get('data', {})
        payment_info = payment_data.get('payment', {})
        
        # Extract payment details
        amount = payment_info.get('amount', 0) / 100  # Convert from cents to reais
        fee = payment_info.get('fee', 80) / 100  # AbacatePay fee in reais
        external_reference = payment_data.get('externalId') or payment_data.get('external_reference')
        
        print(f"🥑 Processing AbacatePay payment success: Amount {amount}, Fee {fee}")
        
        if external_reference:
            # Find and update transaction
            transaction = await db.transactions.find_one({"id": external_reference})
            if transaction:
                # Update transaction status
                await db.transactions.update_one(
                    {"id": external_reference},
                    {"$set": {
                        "status": TransactionStatus.APPROVED,
                        "updated_at": datetime.utcnow(),
                        "fee": fee,
                        "net_amount": amount - fee
                    }}
                )
                
                # Update user balance
                await db.users.update_one(
                    {"id": transaction["user_id"]},
                    {"$inc": {"balance": amount - fee}}
                )
                
                print(f"✅ AbacatePay: Updated user balance +{amount - fee}")
            else:
                print(f"⚠️ Transaction not found: {external_reference}")
        
    except Exception as e:
        print(f"❌ Error processing AbacatePay success: {str(e)}")

async def process_abacatepay_payment_failure(webhook_data: Dict[str, Any]):
    """Process failed AbacatePay payment"""
    try:
        payment_data = webhook_data.get('data', {})
        external_reference = payment_data.get('externalId') or payment_data.get('external_reference')
        
        print(f"🥑 Processing AbacatePay payment failure for: {external_reference}")
        
        if external_reference:
            # Update transaction status
            await db.transactions.update_one(
                {"id": external_reference},
                {"$set": {
                    "status": TransactionStatus.REJECTED,
                    "updated_at": datetime.utcnow()
                }}
            )
            print(f"❌ AbacatePay: Payment failed for transaction {external_reference}")
        
    except Exception as e:
        print(f"❌ Error processing AbacatePay failure: {str(e)}")

async def process_abacatepay_payment_cancellation(webhook_data: Dict[str, Any]):
    """Process cancelled AbacatePay payment"""
    try:
        payment_data = webhook_data.get('data', {})
        external_reference = payment_data.get('externalId') or payment_data.get('external_reference')
        
        print(f"🥑 Processing AbacatePay payment cancellation for: {external_reference}")
        
        if external_reference:
            # Update transaction status
            await db.transactions.update_one(
                {"id": external_reference},
                {"$set": {
                    "status": TransactionStatus.CANCELLED,
                    "updated_at": datetime.utcnow()
                }}
            )
            print(f"⚠️ AbacatePay: Payment cancelled for transaction {external_reference}")
        
    except Exception as e:
        print(f"❌ Error processing AbacatePay cancellation: {str(e)}")

@api_router.post("/payments/withdraw")
async def withdraw_funds(withdraw_request: WithdrawRequest):
    user = await db.users.find_one({"id": withdraw_request.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["balance"] < withdraw_request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Create withdrawal transaction
    transaction = Transaction(
        user_id=withdraw_request.user_id,
        amount=withdraw_request.amount,
        type=TransactionType.WITHDRAWAL,
        status=TransactionStatus.PENDING
    )
    await db.transactions.insert_one(transaction.dict())
    
    # Deduct from user balance
    await db.users.update_one(
        {"id": withdraw_request.user_id},
        {"$inc": {"balance": -withdraw_request.amount}}
    )
    
    # In a real implementation, you would integrate with a transfer API
    # For now, we'll mark it as approved immediately
    await db.transactions.update_one(
        {"id": transaction.id},
        {
            "$set": {
                "status": TransactionStatus.APPROVED,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Withdrawal request processed", "transaction_id": transaction.id}

@api_router.get("/transactions/{user_id}")
async def get_user_transactions(user_id: str):
    transactions = await db.transactions.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
    return [Transaction(**tx) for tx in transactions]

# Bet Routes (Modified for real currency)
@api_router.post("/bets", response_model=Bet)
async def create_bet(bet_data: BetCreate):
    # Check if user exists and has enough balance
    user = await db.users.find_one({"id": bet_data.creator_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["balance"] < bet_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Deduct amount from creator's balance
    await db.users.update_one(
        {"id": bet_data.creator_id},
        {"$inc": {"balance": -bet_data.amount}}
    )
    
    # Create bet debit transaction
    transaction = Transaction(
        user_id=bet_data.creator_id,
        amount=bet_data.amount,
        type=TransactionType.BET_DEBIT,
        status=TransactionStatus.APPROVED
    )
    await db.transactions.insert_one(transaction.dict())
    
    bet_dict = bet_data.dict()
    bet_dict["creator_name"] = user["name"]
    bet = Bet(**bet_dict)
    await db.bets.insert_one(bet.dict())
    return bet

@api_router.post("/bets/{bet_id}/join", response_model=Bet)
async def join_bet(bet_id: str, join_data: JoinBet):
    # Get the bet
    bet = await db.bets.find_one({"id": bet_id})
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    if bet["status"] != BetStatus.WAITING:
        raise HTTPException(status_code=400, detail="Bet is not available to join")
    
    if bet["creator_id"] == join_data.user_id:
        raise HTTPException(status_code=400, detail="Cannot join your own bet")
    
    # Check if user exists and has enough balance
    user = await db.users.find_one({"id": join_data.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["balance"] < bet["amount"]:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Deduct amount from opponent's balance
    await db.users.update_one(
        {"id": join_data.user_id},
        {"$inc": {"balance": -bet["amount"]}}
    )
    
    # Create bet debit transaction for opponent
    transaction = Transaction(
        user_id=join_data.user_id,
        amount=bet["amount"],
        type=TransactionType.BET_DEBIT,
        status=TransactionStatus.APPROVED
    )
    await db.transactions.insert_one(transaction.dict())
    
    # Update bet with opponent info
    await db.bets.update_one(
        {"id": bet_id},
        {
            "$set": {
                "opponent_id": join_data.user_id,
                "opponent_name": user["name"],
                "status": BetStatus.ACTIVE
            }
        }
    )
    
    updated_bet = await db.bets.find_one({"id": bet_id})
    return Bet(**updated_bet)

@api_router.post("/bets/{bet_id}/declare-winner", response_model=Bet)
async def declare_winner(bet_id: str, winner_data: DeclareWinner):
    # Get the bet
    bet = await db.bets.find_one({"id": bet_id})
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    if bet["status"] != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Bet is not active")
    
    # Validate winner is one of the participants
    if winner_data.winner_id not in [bet["creator_id"], bet["opponent_id"]]:
        raise HTTPException(status_code=400, detail="Winner must be one of the participants")
    
    # Get winner info
    winner = await db.users.find_one({"id": winner_data.winner_id})
    if not winner:
        raise HTTPException(status_code=404, detail="Winner not found")
    
    # Calculate platform fee (20% of total pot)
    total_pot = bet["amount"] * 2
    platform_fee = total_pot * 0.20  # 20% platform fee
    winner_payout = total_pot - platform_fee  # 80% to winner
    
    # Transfer winnings to winner (total pot minus 20% platform fee)
    await db.users.update_one(
        {"id": winner_data.winner_id},
        {"$inc": {"balance": winner_payout}}
    )
    
    # Create bet credit transaction for winner (showing net amount received)
    winner_transaction = Transaction(
        user_id=winner_data.winner_id,
        amount=winner_payout,
        type=TransactionType.BET_CREDIT,
        status=TransactionStatus.APPROVED
    )
    await db.transactions.insert_one(winner_transaction.dict())
    
    # Create platform fee transaction for tracking
    platform_transaction = Transaction(
        user_id="platform",  # Special user ID for platform
        amount=platform_fee,
        type=TransactionType.PLATFORM_FEE,  # Fixed enum usage
        status=TransactionStatus.APPROVED
    )
    await db.transactions.insert_one(platform_transaction.dict())
    
    # Update bet status with platform fee information
    await db.bets.update_one(
        {"id": bet_id},
        {
            "$set": {
                "winner_id": winner_data.winner_id,
                "winner_name": winner["name"],
                "status": BetStatus.COMPLETED,
                "completed_at": datetime.utcnow(),
                "platform_fee": platform_fee,
                "winner_payout": winner_payout,
                "total_pot": total_pot
            }
        }
    )
    
    updated_bet = await db.bets.find_one({"id": bet_id})
    return Bet(**updated_bet)

@api_router.get("/bets", response_model=List[Bet])
async def get_all_bets():
    bets = await db.bets.find().sort("created_at", -1).to_list(1000)
    return [Bet(**bet) for bet in bets]

@api_router.get("/bets/waiting", response_model=List[Bet])
async def get_waiting_bets():
    bets = await db.bets.find({"status": BetStatus.WAITING}).sort("created_at", -1).to_list(1000)
    return [Bet(**bet) for bet in bets]

@api_router.get("/bets/user/{user_id}", response_model=List[Bet])
async def get_user_bets(user_id: str):
    bets = await db.bets.find({
        "$or": [
            {"creator_id": user_id},
            {"opponent_id": user_id}
        ]
    }).sort("created_at", -1).to_list(1000)
    return [Bet(**bet) for bet in bets]

@api_router.get("/bets/invite/{invite_code}", response_model=Bet)
async def get_bet_by_invite(invite_code: str):
    """Get bet details by invite code"""
    bet = await db.bets.find_one({"invite_code": invite_code})
    if not bet:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    
    # Check if bet is still valid (not expired)
    current_time = datetime.utcnow()
    if bet["expires_at"] < current_time and bet["status"] == BetStatus.WAITING:
        raise HTTPException(status_code=410, detail="Este convite expirou")
    
    if bet["status"] != BetStatus.WAITING:
        raise HTTPException(status_code=400, detail="Esta aposta não está mais disponível")
    
    return Bet(**bet)

@api_router.post("/bets/join-by-invite/{invite_code}", response_model=Bet)
async def join_bet_by_invite(invite_code: str, join_data: JoinBet):
    """Join bet using invite code"""
    # Get the bet by invite code
    bet = await db.bets.find_one({"invite_code": invite_code})
    if not bet:
        raise HTTPException(status_code=404, detail="Convite não encontrado")
    
    # Check if bet is still valid
    current_time = datetime.utcnow()
    if bet["expires_at"] < current_time and bet["status"] == BetStatus.WAITING:
        raise HTTPException(status_code=410, detail="Este convite expirou")
    
    if bet["status"] != BetStatus.WAITING:
        raise HTTPException(status_code=400, detail="Esta aposta não está mais disponível")
    
    if bet["creator_id"] == join_data.user_id:
        raise HTTPException(status_code=400, detail="Você não pode participar da sua própria aposta")
    
    # Check if user exists and has enough balance
    user = await db.users.find_one({"id": join_data.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if user["balance"] < bet["amount"]:
        raise HTTPException(status_code=400, detail="Saldo insuficiente")
    
    # Deduct amount from opponent's balance
    await db.users.update_one(
        {"id": join_data.user_id},
        {"$inc": {"balance": -bet["amount"]}}
    )
    
    # Create bet debit transaction for opponent
    transaction = Transaction(
        user_id=join_data.user_id,
        amount=bet["amount"],
        type=TransactionType.BET_DEBIT,
        status=TransactionStatus.APPROVED
    )
    await db.transactions.insert_one(transaction.dict())
    
    # Update bet with opponent info
    await db.bets.update_one(
        {"invite_code": invite_code},
        {
            "$set": {
                "opponent_id": join_data.user_id,
                "opponent_name": user["name"],
                "status": BetStatus.ACTIVE
            }
        }
    )
    
    updated_bet = await db.bets.find_one({"invite_code": invite_code})
    return Bet(**updated_bet)

# Health Check
@api_router.get("/")
async def root():
    return {"message": "BetArena API with Payment System is running"}

# Include the router in the main app
app.include_router(api_router)

@app.post("/api/bets/process-expired")
async def process_expired_bets():
    """Process and cancel expired bets, refunding money to creators"""
    current_time = datetime.utcnow()
    
    # Find expired bets that are still waiting
    expired_bets = await db.bets.find({
        "status": BetStatus.WAITING,
        "expires_at": {"$lt": current_time}
    }).to_list(1000)
    
    refunded_count = 0
    
    for bet in expired_bets:
        # Refund money to creator
        await db.users.update_one(
            {"id": bet["creator_id"]},
            {"$inc": {"balance": bet["amount"]}}
        )
        
        # Create refund transaction
        refund_transaction = Transaction(
            user_id=bet["creator_id"],
            amount=bet["amount"],
            type=TransactionType.BET_CREDIT,  # Using bet_credit for refund
            status=TransactionStatus.APPROVED
        )
        await db.transactions.insert_one(refund_transaction.dict())
        
        # Update bet status to expired
        await db.bets.update_one(
            {"id": bet["id"]},
            {
                "$set": {
                    "status": BetStatus.EXPIRED,
                    "completed_at": current_time
                }
            }
        )
        
        refunded_count += 1
    
    return {
        "message": f"Processed {refunded_count} expired bets",
        "refunded_bets": refunded_count
    }

@app.get("/api/bets/check-expiry/{bet_id}")
async def check_bet_expiry(bet_id: str):
    """Check if a specific bet has expired"""
    bet = await db.bets.find_one({"id": bet_id})
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    current_time = datetime.utcnow()
    is_expired = bet["expires_at"] < current_time
    time_remaining = bet["expires_at"] - current_time if not is_expired else None
    
    return {
        "bet_id": bet_id,
        "status": bet["status"],
        "is_expired": is_expired,
        "expires_at": bet["expires_at"],
        "time_remaining_seconds": time_remaining.total_seconds() if time_remaining else 0
    }

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()