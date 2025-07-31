from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
from enum import Enum
import mercadopago
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Mercado Pago setup
mp_access_token = os.environ.get('MERCADO_PAGO_ACCESS_TOKEN')
mp = mercadopago.SDK(mp_access_token) if mp_access_token else None

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

class EventType(str, Enum):
    SPORTS = "sports"
    STOCKS = "stocks"
    CUSTOM = "custom"

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BET_DEBIT = "bet_debit"
    BET_CREDIT = "bet_credit"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone: str
    balance: float = 0.0  # Changed to real currency (BRL)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    name: str
    email: str
    phone: str

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

# User Routes
@api_router.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    # Check if user already exists by email
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        return User(**existing_user)
    
    user = User(**user_data.dict())
    await db.users.insert_one(user.dict())
    return user

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

@api_router.get("/users", response_model=List[User])
async def get_all_users():
    users = await db.users.find().to_list(1000)
    return [User(**user) for user in users]

# Payment Routes
@api_router.post("/payments/create-preference")
async def create_payment_preference(deposit_request: DepositRequest):
    user = await db.users.find_one({"id": deposit_request.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create transaction record
    transaction = Transaction(
        user_id=deposit_request.user_id,
        amount=deposit_request.amount,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.PENDING
    )
    await db.transactions.insert_one(transaction.dict())
    
    # DEMO MODE: Return simulated payment preference
    simulated_preference = {
        "preference_id": f"demo-{transaction.id}",
        "init_point": f"https://sandbox.mercadopago.com.br/checkout/v1/redirect?pref_id=demo-{transaction.id}",
        "sandbox_init_point": f"https://demo-payment-simulator.com/pay?amount={deposit_request.amount}&transaction={transaction.id}",
        "transaction_id": transaction.id,
        "demo_mode": True,
        "message": "MODO DEMONSTRAÇÃO: Use o botão 'Simular Pagamento Aprovado' para aprovar este depósito"
    }
    
    return simulated_preference

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
async def payment_webhook(request: Request):
    try:
        body = await request.body()
        data = json.loads(body)
        
        if data.get("type") == "payment":
            payment_id = data["data"]["id"]
            
            # Get payment details from Mercado Pago
            payment_info = mp.payment().get(payment_id)
            
            if payment_info["status"] == 200:
                payment = payment_info["response"]
                external_reference = payment.get("external_reference")
                
                if external_reference:
                    # Find transaction
                    transaction = await db.transactions.find_one({"id": external_reference})
                    
                    if transaction:
                        if payment["status"] == "approved":
                            # Update transaction status
                            await db.transactions.update_one(
                                {"id": external_reference},
                                {
                                    "$set": {
                                        "status": TransactionStatus.APPROVED,
                                        "mp_payment_id": payment_id,
                                        "updated_at": datetime.utcnow()
                                    }
                                }
                            )
                            
                            # Add balance to user
                            await db.users.update_one(
                                {"id": transaction["user_id"]},
                                {"$inc": {"balance": transaction["amount"]}}
                            )
                            
                        elif payment["status"] in ["rejected", "cancelled"]:
                            await db.transactions.update_one(
                                {"id": external_reference},
                                {
                                    "$set": {
                                        "status": TransactionStatus.REJECTED,
                                        "mp_payment_id": payment_id,
                                        "updated_at": datetime.utcnow()
                                    }
                                }
                            )
        
        return {"status": "ok"}
    
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        return {"status": "error"}

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
    
    # Transfer winnings (bet amount x 2) to winner
    total_winnings = bet["amount"] * 2
    await db.users.update_one(
        {"id": winner_data.winner_id},
        {"$inc": {"balance": total_winnings}}
    )
    
    # Create bet credit transaction for winner
    transaction = Transaction(
        user_id=winner_data.winner_id,
        amount=total_winnings,
        type=TransactionType.BET_CREDIT,
        status=TransactionStatus.APPROVED
    )
    await db.transactions.insert_one(transaction.dict())
    
    # Update bet status
    await db.bets.update_one(
        {"id": bet_id},
        {
            "$set": {
                "winner_id": winner_data.winner_id,
                "winner_name": winner["name"],
                "status": BetStatus.COMPLETED,
                "completed_at": datetime.utcnow()
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

# Health Check
@api_router.get("/")
async def root():
    return {"message": "BetArena API with Payment System is running"}

# Include the router in the main app
app.include_router(api_router)

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