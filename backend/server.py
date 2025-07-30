from fastapi import FastAPI, APIRouter, HTTPException
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    balance: int = 1000  # Starting with 1000 points
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    name: str

class Bet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_title: str
    event_type: EventType
    event_description: str
    amount: int
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
    amount: int
    creator_id: str

class JoinBet(BaseModel):
    user_id: str

class DeclareWinner(BaseModel):
    winner_id: str

# User Routes
@api_router.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"name": user_data.name})
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

# Bet Routes
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
    return {"message": "Betting Platform API is running"}

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