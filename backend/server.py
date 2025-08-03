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
from abacatepay.products import Product

import json
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# AbacatePay Configuration with HTTPS validation
abacate_api_token = os.environ.get('ABACATEPAY_API_TOKEN')
abacate_webhook_secret = os.environ.get('ABACATEPAY_WEBHOOK_SECRET')
abacate_webhook_id = os.environ.get('ABACATEPAY_WEBHOOK_ID')

# HTTPS validation for webhook security
def ensure_https_url(url: str) -> str:
    """Ensure URL uses HTTPS for webhook security"""
    if not url:
        return "https://localhost:3000"
    
    if url.startswith('http://'):
        # Convert HTTP to HTTPS for webhook security
        url = url.replace('http://', 'https://')
        print(f"⚠️ WARNING: Converted HTTP to HTTPS for webhook security: {url}")
    elif not url.startswith('https://'):
        # Add HTTPS if no protocol specified
        url = f"https://{url}"
        print(f"⚠️ WARNING: Added HTTPS protocol for webhook security: {url}")
    
    return url

def generate_webhook_url(base_url: str, secret: str) -> str:
    """Generate secure HTTPS webhook URL"""
    base_url = ensure_https_url(base_url)
    webhook_url = f"{base_url}/api/payments/webhook?webhookSecret={secret}"
    
    # Final HTTPS validation
    if not webhook_url.startswith('https://'):
        raise ValueError(f"🚨 SECURITY ERROR: Webhook URL must use HTTPS: {webhook_url}")
    
    print(f"🔒 Generated secure webhook URL: {webhook_url}")
    return webhook_url

# Ensure frontend URL is always HTTPS for webhook security
frontend_url = ensure_https_url(os.environ.get('FRONTEND_URL', 'https://localhost:3000'))
print(f"🔒 Frontend URL (HTTPS enforced): {frontend_url}")

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
    if abacate_webhook_id:
        print(f"🆔 Webhook ID: {abacate_webhook_id}")
        print(f"✅ Webhook configured and active in AbacatePay dashboard")
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

# Webhook processing cache to prevent duplicates
webhook_processing_cache = {}
WEBHOOK_CACHE_TTL = 300  # 5 minutes cache

def is_webhook_already_processed(webhook_data: Dict[str, Any]) -> bool:
    """Check if this webhook has already been processed to prevent duplicates"""
    try:
        # Create a unique identifier for this webhook
        payment_data = webhook_data.get('data', {})
        payment_info = payment_data.get('payment', {})
        pix_info = payment_data.get('pixQrCode', {})
        
        # Create unique hash based on payment details
        unique_data = {
            'event': webhook_data.get('event'),
            'amount': payment_info.get('amount'),
            'fee': payment_info.get('fee'),
            'pix_id': pix_info.get('id'),
            'pix_status': pix_info.get('status'),
            'dev_mode': webhook_data.get('devMode', False)
        }
        
        import hashlib
        webhook_hash = hashlib.md5(str(unique_data).encode()).hexdigest()
        
        current_time = datetime.utcnow()
        
        # Check if this webhook was processed recently
        if webhook_hash in webhook_processing_cache:
            last_processed = webhook_processing_cache[webhook_hash]
            time_diff = (current_time - last_processed).total_seconds()
            
            if time_diff < WEBHOOK_CACHE_TTL:
                print(f"🚫 DUPLICATE WEBHOOK DETECTED - Hash: {webhook_hash[:8]}...")
                print(f"   Last processed: {time_diff:.1f} seconds ago")
                print(f"   Skipping duplicate processing")
                return True
        
        # Mark this webhook as processed
        webhook_processing_cache[webhook_hash] = current_time
        
        # Clean old entries from cache
        expired_keys = [
            key for key, timestamp in webhook_processing_cache.items()
            if (current_time - timestamp).total_seconds() > WEBHOOK_CACHE_TTL
        ]
        for key in expired_keys:
            del webhook_processing_cache[key]
        
        print(f"✅ NEW WEBHOOK - Hash: {webhook_hash[:8]}... (Processing)")
        return False
        
    except Exception as e:
        print(f"⚠️ Error checking webhook duplication: {str(e)}")
        return False  # Process webhook if unsure

# Admin authentication middleware
async def verify_admin_access(user_id: str):
    """Verify if user has admin privileges"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=403, 
            detail="Acesso negado. Apenas administradores podem acessar esta funcionalidade."
        )
    
    print(f"✅ Admin access verified for user: {user['name']} ({user_id})")
    return user

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone: str
    password_hash: str  # Added password hash field
    email_verified: bool = False  # Email verification status
    email_verification_token: Optional[str] = None  # Token for email verification
    is_admin: bool = False  # Added admin flag
    balance: float = 0.0  # Changed to real currency (BRL)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

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
    type: TransactionType
    amount: float
    fee: float = 0.0  # Platform fee
    net_amount: float  # Amount after fee
    status: TransactionStatus = TransactionStatus.PENDING
    external_reference: Optional[str] = None  # Reference from payment provider
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LoginLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    email: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    login_time: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    failure_reason: Optional[str] = None

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
    
    # New fields for automatic matching system
    side: str  # "A" or "B" (e.g., "Brasil" or "Argentina")  
    event_id: str  # Common event ID for matching (e.g., "brasil_vs_argentina")
    side_name: str = ""  # Human readable side name (e.g., "Brasil", "Argentina")

class BetCreate(BaseModel):
    event_title: str
    event_type: EventType
    event_description: str
    amount: float
    creator_id: str
    side: str  # "A" or "B" (e.g., "Brasil" or "Argentina")
    event_id: str  # Common event ID for matching (e.g., "brasil_vs_argentina")
    side_name: str  # Human readable side name (e.g., "Brasil", "Argentina")

class JoinBet(BaseModel):
    user_id: str

class DeclareWinner(BaseModel):
    winner_id: str
    admin_user_id: str  # ID do administrador que está declarando o vencedor

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
        raise HTTPException(status_code=400, detail="Usuário com este email já existe")
    
    # Validate email format
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, user_data.email):
        raise HTTPException(status_code=400, detail="Formato de email inválido")
    
    # Validate password strength
    if len(user_data.password) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 6 caracteres")
    
    # Hash the password
    password_hash = hash_password(user_data.password)
    
    # Generate email verification token
    import secrets
    verification_token = secrets.token_urlsafe(32)
    
    # Create user with hashed password and email verification fields
    user_dict = user_data.dict()
    user_dict.pop('password')  # Remove plain password
    user_dict['password_hash'] = password_hash
    user_dict['email_verified'] = False  # Initially not verified
    user_dict['email_verification_token'] = verification_token
    
    user = User(**user_dict)
    await db.users.insert_one(user.dict())
    
    print(f"📧 New user created (email verification required): {user_data.email}")
    print(f"🔐 Verification token: {verification_token}")
    
    # TODO: Send verification email with SendGrid when credentials are available
    # For now, we'll manually verify users or provide a verification endpoint
    
    # Return user data without password hash and verification token
    user_response_dict = user.dict()
    user_response_dict.pop('password_hash', None)
    user_response_dict.pop('email_verification_token', None)
    
    return UserResponse(**user_response_dict)

@api_router.post("/users/login", response_model=UserResponse)
async def login_user(login_data: UserLogin, request: Request):
    """Login user with email and password - requires verified email"""
    # Function to log login attempts
    async def log_login_attempt(user_id: str, email: str, success: bool, failure_reason: str = None):
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        login_log = LoginLog(
            user_id=user_id if user_id else "unknown",
            email=email,
            ip_address=client_ip,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason
        )
        await db.login_logs.insert_one(login_log.dict())
    
    # Find user by email
    user = await db.users.find_one({"email": login_data.email})
    if not user:
        await log_login_attempt("unknown", login_data.email, False, "Email not found")
        raise HTTPException(status_code=401, detail="Email não encontrado ou não verificado")
    
    # Check if email is verified
    if not user.get("email_verified", False):
        await log_login_attempt(user["id"], login_data.email, False, "Email not verified")
        raise HTTPException(
            status_code=401, 
            detail="Email não verificado. Verifique seu email para confirmar sua conta."
        )
    
    # Verify password
    if not verify_password(login_data.password, user["password_hash"]):
        await log_login_attempt(user["id"], login_data.email, False, "Invalid password")
        raise HTTPException(status_code=401, detail="Senha incorreta")
    
    # Update last login time
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Log successful login
    await log_login_attempt(user["id"], login_data.email, True)
    
    print(f"✅ User logged in successfully: {login_data.email} (verified)")
    return UserResponse(**user)

@api_router.post("/users/check-email")
async def check_email_exists(email: str):
    """Check if email exists in system"""
    user = await db.users.find_one({"email": email})
    return {"exists": user is not None}

@api_router.post("/users/verify-email/{verification_token}")
async def verify_email(verification_token: str):
    """Verify user email with token"""
    user = await db.users.find_one({"email_verification_token": verification_token})
    if not user:
        raise HTTPException(status_code=404, detail="Token de verificação inválido ou expirado")
    
    if user.get("email_verified", False):
        return {"message": "Email já verificado", "verified": True}
    
    # Mark email as verified
    await db.users.update_one(
        {"email_verification_token": verification_token},
        {
            "$set": {"email_verified": True},
            "$unset": {"email_verification_token": ""}
        }
    )
    
    print(f"✅ Email verified for user: {user['email']}")
    return {"message": "Email verificado com sucesso!", "verified": True}

@api_router.post("/users/manual-verify")
async def manual_verify_email(email: str):
    """Manually verify email (admin function - temporary)"""
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if user.get("email_verified", False):
        return {"message": "Email já verificado", "verified": True}
    
    # Mark email as verified
    await db.users.update_one(
        {"email": email},
        {
            "$set": {"email_verified": True},
            "$unset": {"email_verification_token": ""}
        }
    )
    
    print(f"✅ Email manually verified for user: {email}")
    return {"message": f"Email {email} verificado manualmente!", "verified": True}

@api_router.get("/users/{user_id}")
async def get_user_by_id(user_id: str):
    """Get user data by ID including admin status"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Return user data without sensitive information
    user_data = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "phone": user["phone"],
        "is_admin": user.get("is_admin", False),
        "balance": user.get("balance", 0.0),
        "created_at": user.get("created_at"),
        "last_login": user.get("last_login"),
        "email_verified": user.get("email_verified", False)
    }
    
    print(f"📋 User data requested for: {user['name']} (Admin: {user_data['is_admin']})")
    return user_data

@api_router.get("/users")
async def get_all_users():
    """Get all users for admin purposes"""
    cursor = db.users.find({}, {"password_hash": 0, "email_verification_token": 0})
    users = await cursor.to_list(length=100)
    return users

@api_router.get("/users/{user_id}/login-logs")
async def get_user_login_logs(user_id: str, limit: int = 10):
    """Get login logs for a specific user"""
    cursor = db.login_logs.find({"user_id": user_id}).sort("login_time", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    
    # Format logs for response
    formatted_logs = []
    for log in logs:
        formatted_log = {
            "id": log["id"],
            "email": log["email"], 
            "ip_address": log.get("ip_address", "unknown"),
            "user_agent": log.get("user_agent", "unknown")[:100] + "..." if len(log.get("user_agent", "")) > 100 else log.get("user_agent", "unknown"),
            "login_time": log["login_time"].isoformat(),
            "success": log["success"],
            "failure_reason": log.get("failure_reason")
        }
        formatted_logs.append(formatted_log)
    
    return {"login_logs": formatted_logs}

@api_router.get("/admin/login-logs")
async def get_all_login_logs(limit: int = 50):
    """Get all login logs (admin only)"""
    cursor = db.login_logs.find({}).sort("login_time", -1).limit(limit)
    logs = await cursor.to_list(length=limit)
    
    # Format logs for response
    formatted_logs = []
    for log in logs:
        formatted_log = {
            "id": log["id"],
            "user_id": log["user_id"],
            "email": log["email"],
            "ip_address": log.get("ip_address", "unknown"),
            "user_agent": log.get("user_agent", "unknown")[:100] + "..." if len(log.get("user_agent", "")) > 100 else log.get("user_agent", "unknown"),
            "login_time": log["login_time"].isoformat(),
            "success": log["success"],
            "failure_reason": log.get("failure_reason")
        }
        formatted_logs.append(formatted_log)
    
    return {"login_logs": formatted_logs}

@api_router.post("/payments/check-status/{transaction_id}")
async def check_payment_status(transaction_id: str):
    """Manual payment status check - for when webhook is not working"""
    try:
        # Find the transaction
        transaction = await db.transactions.find_one({"id": transaction_id})
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        print(f"🔍 Manual payment status check for transaction: {transaction_id}")
        
        # If already approved, return current status
        if transaction.get("status") == TransactionStatus.APPROVED:
            return {
                "transaction_id": transaction_id,
                "status": "approved",
                "balance_updated": True,
                "message": "Payment already processed"
            }
        
        # Check with AbacatePay API if payment was completed
        if abacatepay_client and abacate_valid:
            try:
                # Get payment details from AbacatePay
                payment_id = transaction.get("payment_id") or transaction.get("external_reference")
                if payment_id:
                    # Try to get payment status from AbacatePay
                    payment_details = abacatepay_client.billing.retrieve(payment_id)
                    
                    print(f"🥑 AbacatePay payment status: {payment_details}")
                    
                    # If payment is completed, process it
                    if hasattr(payment_details, 'status') and payment_details.status == 'paid':
                        print(f"✅ Payment confirmed as paid, processing...")
                        
                        # Simulate webhook data for processing
                        webhook_data = {
                            "event": "billing.paid",
                            "data": {
                                "externalId": transaction_id,
                                "payment": {
                                    "amount": int(transaction["amount"] * 100),
                                    "fee": 80  # R$ 0.80 in cents
                                }
                            }
                        }
                        
                        # Process the payment
                        await process_abacatepay_payment_success(webhook_data)
                        
                        return {
                            "transaction_id": transaction_id,
                            "status": "approved",
                            "balance_updated": True,
                            "message": "Payment confirmed and balance updated!"
                        }
                    else:
                        return {
                            "transaction_id": transaction_id,
                            "status": "pending",
                            "balance_updated": False,
                            "message": f"Payment still pending on AbacatePay: {payment_details.status if hasattr(payment_details, 'status') else 'unknown'}"
                        }
                        
            except Exception as api_error:
                print(f"⚠️ AbacatePay API check failed: {str(api_error)}")
                return {
                    "transaction_id": transaction_id,
                    "status": "pending",
                    "balance_updated": False,
                    "message": f"Could not check with AbacatePay: {str(api_error)}"
                }
        
        return {
            "transaction_id": transaction_id,
            "status": "pending",
            "balance_updated": False,
            "message": "Payment still pending - webhook not configured"
        }
        
    except Exception as e:
        print(f"❌ Payment status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@api_router.post("/payments/manual-approve/{transaction_id}")
async def manual_approve_payment(transaction_id: str, amount: float):
    """Manually approve payment - temporary solution for webhook issues"""
    try:
        # Find the transaction
        transaction = await db.transactions.find_one({"id": transaction_id})
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        if transaction.get("status") == TransactionStatus.APPROVED:
            return {"message": "Payment already approved", "status": "already_approved"}
        
        print(f"🔧 Manual payment approval for transaction: {transaction_id}")
        
        # Simulate webhook data
        webhook_data = {
            "event": "billing.paid", 
            "data": {
                "externalId": transaction_id,
                "payment": {
                    "amount": int(amount * 100),
                    "fee": 80  # R$ 0.80 in cents
                }
            }
        }
        
        # Process the payment
        await process_abacatepay_payment_success(webhook_data)
        
        return {
            "transaction_id": transaction_id,
            "status": "approved",
            "message": "Payment manually approved and balance updated!",
            "amount": amount,
            "fee": 0.80,
            "net_amount": amount - 0.80
        }
        
    except Exception as e:
        print(f"❌ Manual approval error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Manual approval failed: {str(e)}")

# Payment Routes (Modified for real currency)
@api_router.post("/payments/create-preference")
async def create_payment_preference(request: CreatePaymentRequest):
    """Create payment preference using AbacatePay"""
    
    if not abacatepay_client or not abacate_valid:
        # Return demo mode when AbacatePay is not properly configured
        fee = 0.80  # AbacatePay fixed fee
        net_amount = request.amount - fee
        
        transaction = Transaction(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            type=TransactionType.DEPOSIT,
            amount=request.amount,
            fee=fee,
            net_amount=net_amount,
            status=TransactionStatus.PENDING,
            description="Depósito demo - AbacatePay não configurado",
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
    
    # Create transaction record with fee calculation
    fee = 0.80  # AbacatePay fixed fee
    net_amount = request.amount - fee
    
    transaction = Transaction(
        id=str(uuid.uuid4()),
        user_id=request.user_id,
        type=TransactionType.DEPOSIT,
        amount=request.amount,
        fee=fee,
        net_amount=net_amount,
        status=TransactionStatus.PENDING,
        description=f"Depósito AbacatePay - {user['name']}",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    await db.transactions.insert_one(transaction.dict())
    
    try:
        # Create product using correct AbacatePay Product class
        product = Product(
            external_id=transaction.id,
            name="BET ARENA - Depósito",
            quantity=1,
            price=int(request.amount * 100),  # Convert to cents
            description=f"Depósito BetArena - {user['name']}"
        )
        
        # Create billing with AbacatePay using correct API
        # Ensure email is valid format for AbacatePay
        user_email = user.get("email", "")
        if not user_email or "@" not in user_email:
            user_email = f"user_{transaction.id}@betarena.com"
        
        # Create billing data dictionary
        # Note: webhook_url is configured in AbacatePay dashboard, not in API
        billing_data = {
            "products": [product],
            "return_url": f"{frontend_url}/payment-success",
            "completion_url": f"{frontend_url}/payment-success", 
            "customer": {
                "name": user["name"],
                "email": user_email,
                "cellphone": user.get("phone", "11999999999"),
                "tax_id": "11144477735"  # Valid test CPF for AbacatePay
            },
            "frequency": 'ONE_TIME'  # Required parameter for AbacatePay API
        }
        
        print(f"🥑 AbacatePay billing created - Webhook must be configured in dashboard")
        secure_webhook_url = generate_webhook_url(frontend_url, abacate_webhook_secret)
        print(f"🔗 Required HTTPS webhook URL for dashboard: {secure_webhook_url}")
        
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
            "message": f"Pagamento via AbacatePay configurado com sucesso! Taxa: R$ 0,80",
            "webhook_status": "configure_webhook_in_dashboard",
            "webhook_url_needed": generate_webhook_url(frontend_url, abacate_webhook_secret)
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

@api_router.get("/payments/webhook-test")
async def test_webhook_endpoint():
    """Test webhook endpoint accessibility"""
    secure_webhook_url = generate_webhook_url(frontend_url, abacate_webhook_secret)
    return {
        "status": "webhook_accessible",
        "message": "Webhook endpoint is accessible",
        "expected_url": secure_webhook_url,
        "webhook_secret": abacate_webhook_secret,
        "webhook_id": abacate_webhook_id,
        "webhook_configured": bool(abacate_webhook_id),
        "timestamp": datetime.utcnow().isoformat(),
        "https_enforced": True
    }

@api_router.post("/payments/webhook")
async def webhook_abacatepay(request: Request):
    """AbacatePay webhook endpoint with duplicate protection"""
    start_time = datetime.utcnow()
    
    try:
        # Get client IP for logging
        client_ip = request.client.host if request.client else "unknown"
        print(f"🥑 AbacatePay Webhook received from IP: {client_ip} at {start_time.isoformat()}")
        
        # Validate webhook secret from query parameters
        webhook_secret = request.query_params.get('webhookSecret')
        print(f"🔐 Webhook secret provided: {'Yes' if webhook_secret else 'No'}")
        
        if not webhook_secret or webhook_secret != abacate_webhook_secret:
            print(f"❌ Invalid AbacatePay webhook secret. Expected: {abacate_webhook_secret[:10]}...")
            print(f"❌ Received: {webhook_secret[:10] + '...' if webhook_secret else 'None'}")
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

        # Parse webhook payload
        webhook_data = await request.json()
        event_type = webhook_data.get('event')
        
        print(f"🥑 AbacatePay Webhook Event: {event_type}")

        result = {"received": True, "event": event_type}

        if event_type == 'billing.paid':
            process_result = await process_abacatepay_payment_success(webhook_data)
            result.update(process_result or {})
        elif event_type == 'billing.failed':
            await process_abacatepay_payment_failure(webhook_data)
        elif event_type == 'billing.cancelled':
            await process_abacatepay_payment_cancellation(webhook_data)
        else:
            print(f"⚠️ Unknown AbacatePay webhook event: {event_type}")
            result["warning"] = f"Unknown event type: {event_type}"

        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        result.update({
            "message": f"Webhook processed successfully: {event_type}",
            "processing_time_seconds": processing_time,
            "processed_at": end_time.isoformat()
        })
        
        print(f"✅ Webhook processing completed in {processing_time:.3f} seconds")
        return result
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        print(f"❌ AbacatePay Webhook Error after {processing_time:.3f} seconds: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Webhook processing error: {str(e)}")

async def process_abacatepay_payment_success(webhook_data: Dict[str, Any]):
    """Process successful AbacatePay payment with duplicate protection"""
    try:
        print(f"🥑 AbacatePay payment success webhook received")
        
        # Check for duplicate webhook processing
        if is_webhook_already_processed(webhook_data):
            print(f"🚫 DUPLICATE WEBHOOK IGNORED - Preventing multiple processing")
            return {"status": "duplicate_ignored", "message": "Webhook already processed"}
        
        print(f"🥑 Processing NEW webhook - Full payload: {json.dumps(webhook_data, indent=2)}")
        
        payment_data = webhook_data.get('data', {})
        payment_info = payment_data.get('payment', {})
        pix_info = payment_data.get('pixQrCode', {})
        
        # Extract payment details from real AbacatePay format
        amount = payment_info.get('amount', 0) / 100  # Convert from cents to reais
        fee = payment_info.get('fee', 80) / 100  # AbacatePay fee in reais
        
        print(f"🥑 Processing AbacatePay payment success:")
        print(f"   Amount: R$ {amount}")
        print(f"   Fee: R$ {fee}")
        print(f"   Net Amount: R$ {amount - fee}")
        print(f"   PIX Status: {pix_info.get('status', 'unknown')}")
        
        # Try multiple approaches to find the transaction
        external_reference = None
        billing_id = pix_info.get('id', '').strip()
        
        # Method 1: Look for external_reference in various places
        external_reference = (
            payment_data.get('externalId') or 
            payment_data.get('external_reference') or
            payment_info.get('externalId') or 
            payment_info.get('external_reference')
        )
        
        print(f"🔍 Looking for transaction with:")
        print(f"   External Reference: {external_reference}")
        print(f"   Billing ID: {billing_id}")
        
        transaction = None
        
        # Method 1: Find by external_reference if available
        if external_reference:
            transaction = await db.transactions.find_one({"id": external_reference})
            print(f"📋 Transaction found by external_reference: {'Yes' if transaction else 'No'}")
        
        # Method 2: Find by payment_id (billing ID)
        if not transaction and billing_id:
            transaction = await db.transactions.find_one({"payment_id": billing_id})
            print(f"📋 Transaction found by payment_id: {'Yes' if transaction else 'No'}")
        
        # Method 3: Find pending transaction with matching amount (fallback)
        if not transaction and amount > 0:
            transaction = await db.transactions.find_one({
                "amount": amount,
                "status": TransactionStatus.PENDING,
                "type": TransactionType.DEPOSIT
            })
            print(f"📋 Transaction found by amount matching: {'Yes' if transaction else 'No'}")
        
        if transaction:
            # CRITICAL: Check if transaction was already processed to prevent double crediting
            if transaction.get("status") == TransactionStatus.APPROVED:
                print(f"🚫 TRANSACTION ALREADY APPROVED - Preventing double credit")
                print(f"   Transaction ID: {transaction['id']}")
                print(f"   User: {transaction['user_id']}")
                return {"status": "already_processed", "message": "Transaction already approved"}
            
            print(f"✅ Found PENDING transaction for user: {transaction['user_id']}")
            print(f"   Transaction ID: {transaction['id']}")
            print(f"   Original Amount: R$ {transaction['amount']}")
            
            # Update transaction status atomically to prevent race conditions
            result = await db.transactions.update_one(
                {
                    "id": transaction["id"],
                    "status": TransactionStatus.PENDING  # Only update if still pending
                },
                {"$set": {
                    "status": TransactionStatus.APPROVED,
                    "updated_at": datetime.utcnow(),
                    "fee": fee,
                    "net_amount": amount - fee,
                    "external_reference": billing_id,
                    "payment_method": "PIX",
                    "webhook_processed_at": datetime.utcnow()
                }}
            )
            
            if result.modified_count == 0:
                print(f"🚫 RACE CONDITION DETECTED - Transaction already processed by another webhook")
                return {"status": "race_condition", "message": "Transaction already being processed"}
            
            print(f"✅ Transaction updated to APPROVED (atomic update successful)")
            
            # Get current user balance before update
            user = await db.users.find_one({"id": transaction["user_id"]})
            old_balance = user.get("balance", 0) if user else 0
            
            # Update user balance atomically
            credit_amount = amount - fee
            update_result = await db.users.update_one(
                {"id": transaction["user_id"]},
                {"$inc": {"balance": credit_amount}}
            )
            
            if update_result.modified_count == 0:
                print(f"⚠️ WARNING: User balance update failed")
                return {"status": "balance_update_failed", "message": "Failed to update user balance"}
            
            # Get updated balance
            updated_user = await db.users.find_one({"id": transaction["user_id"]})
            new_balance = updated_user.get("balance", 0) if updated_user else 0
            
            print(f"✅ AbacatePay: Balance updated for user {transaction['user_id']}")
            print(f"   Old balance: R$ {old_balance:.2f}")
            print(f"   Credit amount: +R$ {credit_amount:.2f}")
            print(f"   New balance: R$ {new_balance:.2f}")
            
            # Success notification
            print(f"🎉 PAYMENT PROCESSED SUCCESSFULLY (NO DUPLICATES)!")
            print(f"   User: {transaction['user_id']}")
            print(f"   Amount: R$ {amount:.2f}")
            print(f"   Fee: R$ {fee:.2f}")
            print(f"   Net Credit: R$ {credit_amount:.2f}")
            
            return {"status": "processed", "message": "Payment processed successfully", "amount": credit_amount}
            
        else:
            print(f"❌ Transaction not found for AbacatePay payment")
            print("🔍 Available recent transactions:")
            cursor = db.transactions.find({"status": "PENDING"}).sort("created_at", -1).limit(5)
            async for tx in cursor:
                print(f"  - Transaction ID: {tx.get('id')}")
                print(f"    Amount: R$ {tx.get('amount', 0):.2f}")
                print(f"    User: {tx.get('user_id')}")
                print(f"    Payment ID: {tx.get('payment_id', 'none')}")
                
            return {"status": "transaction_not_found", "message": "No matching transaction found"}
        
    except Exception as e:
        print(f"❌ Error processing AbacatePay success: {str(e)}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        raise e

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
    fee = 0.0  # No fee for withdrawal
    net_amount = withdraw_request.amount
    
    transaction = Transaction(
        user_id=withdraw_request.user_id,
        amount=withdraw_request.amount,
        fee=fee,
        net_amount=net_amount,
        type=TransactionType.WITHDRAWAL,
        status=TransactionStatus.PENDING,
        description="Saque de fundos"
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

@api_router.post("/admin/make-admin/{user_email}")
async def make_user_admin(user_email: str):
    """Make a user admin - TEMPORARY ENDPOINT for initial setup"""
    user = await db.users.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Update user to admin
    await db.users.update_one(
        {"email": user_email},
        {"$set": {"is_admin": True}}
    )
    
    print(f"✅ User {user['name']} ({user_email}) is now an administrator")
    return {
        "message": f"Usuário {user['name']} agora é administrador",
        "user_id": user["id"],
        "user_name": user["name"],
        "email": user_email,
        "is_admin": True
    }

@api_router.get("/admin/check-admin/{user_id}")
async def check_admin_status(user_id: str):
    """Check if a user is admin"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    return {
        "user_id": user_id,
        "name": user["name"],
        "email": user["email"],
        "is_admin": user.get("is_admin", False)
    }

async def find_matching_bet(event_id: str, side: str, amount: float) -> Optional[Dict]:
    """Find a matching bet for automatic pairing"""
    # Look for opposite side bet with same event_id and amount
    opposite_side = "B" if side == "A" else "A"
    
    matching_bet = await db.bets.find_one({
        "event_id": event_id,
        "side": opposite_side,
        "amount": amount,
        "status": BetStatus.WAITING,
        "opponent_id": None  # Still looking for opponent
    })
    
    if matching_bet:
        print(f"🎯 Found matching bet for event {event_id}: {matching_bet['id']}")
        print(f"   Original side: {side}, Matching side: {opposite_side}")
    
    return matching_bet

async def connect_bets(bet1_id: str, bet2_id: str, user2_id: str, user2_name: str):
    """Connect two matching bets"""
    try:
        # Update the original bet with opponent info
        await db.bets.update_one(
            {"id": bet1_id},
            {"$set": {
                "opponent_id": user2_id,
                "opponent_name": user2_name,
                "status": BetStatus.ACTIVE
            }}
        )
        
        # Mark the second bet as connected (we'll keep both for reference)
        await db.bets.update_one(
            {"id": bet2_id},
            {"$set": {
                "opponent_id": "MATCHED",  # Special marker
                "status": BetStatus.ACTIVE
            }}
        )
        
        print(f"✅ Connected bets: {bet1_id} ↔ {bet2_id}")
        
        return True
    except Exception as e:
        print(f"❌ Error connecting bets: {str(e)}")
        return False

# Bet Routes (Modified for real currency)
@api_router.post("/bets", response_model=Bet)
async def create_bet(bet_data: BetCreate):
    """Create a new bet with automatic matching system"""
    print(f"🎯 Creating bet for event: {bet_data.event_id}, side: {bet_data.side} ({bet_data.side_name})")
    
    # Check if user exists and has enough balance
    user = await db.users.find_one({"id": bet_data.creator_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user["balance"] < bet_data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Look for matching bet FIRST (before deducting balance)
    matching_bet = await find_matching_bet(bet_data.event_id, bet_data.side, bet_data.amount)
    
    # Deduct amount from creator's balance
    await db.users.update_one(
        {"id": bet_data.creator_id},
        {"$inc": {"balance": -bet_data.amount}}
    )
    
    # Create bet debit transaction
    fee = 0.0  # No fee for bet creation
    net_amount = bet_data.amount
    
    transaction = Transaction(
        user_id=bet_data.creator_id,
        amount=bet_data.amount,
        fee=fee,
        net_amount=net_amount,
        type=TransactionType.BET_DEBIT,
        status=TransactionStatus.APPROVED,
        description=f"Aposta criada - {bet_data.event_description} ({bet_data.side_name})"
    )
    await db.transactions.insert_one(transaction.dict())
    
    # Create the new bet
    bet_dict = bet_data.dict()
    bet_dict["creator_name"] = user["name"]
    bet = Bet(**bet_dict)
    
    # Check if we found a matching bet for automatic connection
    if matching_bet:
        print(f"🎉 AUTO-MATCHING: Found opposite bet!")
        print(f"   Original bet: {matching_bet['side']} ({matching_bet.get('side_name', 'Unknown')})")
        print(f"   New bet: {bet.side} ({bet.side_name})")
        
        # Connect the bets automatically
        bet.opponent_id = matching_bet["creator_id"]
        bet.opponent_name = matching_bet["creator_name"] 
        bet.status = BetStatus.ACTIVE
        
        # Also deduct from the matching bet's creator (if not already done)
        matching_user = await db.users.find_one({"id": matching_bet["creator_id"]})
        if matching_user and matching_user["balance"] >= matching_bet["amount"]:
            await db.users.update_one(
                {"id": matching_bet["creator_id"]},
                {"$inc": {"balance": -matching_bet["amount"]}}
            )
            
            # Create transaction for matching bet user
            matching_transaction = Transaction(
                user_id=matching_bet["creator_id"],
                amount=matching_bet["amount"],
                fee=0.0,
                net_amount=matching_bet["amount"],
                type=TransactionType.BET_DEBIT,
                status=TransactionStatus.APPROVED,
                description=f"Aposta conectada - {bet_data.event_description} ({matching_bet.get('side_name', 'Unknown')})"
            )
            await db.transactions.insert_one(matching_transaction.dict())
        
        # Update the original matching bet
        success = await connect_bets(matching_bet["id"], bet.id, bet.creator_id, bet.creator_name)
        
        if success:
            print(f"✅ BETS CONNECTED AUTOMATICALLY!")
            print(f"   {matching_bet['creator_name']} ({matching_bet['side']}) vs {bet.creator_name} ({bet.side})")
        else:
            print(f"⚠️ Failed to connect bets, bet will remain in waiting status")
    else:
        print(f"⏳ No matching bet found, bet will wait for opponent")
    
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
    fee = 0.0  # No fee for bet join
    net_amount = bet["amount"]
    
    transaction = Transaction(
        user_id=join_data.user_id,
        amount=bet["amount"],
        fee=fee,
        net_amount=net_amount,
        type=TransactionType.BET_DEBIT,
        status=TransactionStatus.APPROVED,
        description=f"Aposta aceita - {bet['event_description']}"
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
    """Declare winner of a bet - ADMIN ONLY"""
    
    # CRITICAL: Verify admin access first
    admin_user = await verify_admin_access(winner_data.admin_user_id)
    print(f"🔒 Admin {admin_user['name']} is declaring winner for bet {bet_id}")
    
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
        amount=total_pot,
        fee=platform_fee,
        net_amount=winner_payout,
        type=TransactionType.BET_CREDIT,
        status=TransactionStatus.APPROVED,
        description=f"Vitória na aposta - {bet['event_description']}"
    )
    await db.transactions.insert_one(winner_transaction.dict())
    
    # Create platform fee transaction for tracking
    platform_transaction = Transaction(
        user_id="platform",  # Special user ID for platform
        amount=platform_fee,
        fee=0.0,
        net_amount=platform_fee,
        type=TransactionType.PLATFORM_FEE,  # Fixed enum usage
        status=TransactionStatus.APPROVED,
        description=f"Taxa da plataforma (20%) - {bet['event_description']}"
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

@api_router.get("/bets/waiting")
async def get_waiting_bets():
    """Get all waiting bets that haven't expired"""
    current_time = datetime.utcnow()
    bets = await db.bets.find({
        "status": BetStatus.WAITING,
        "expires_at": {"$gt": current_time}
    }).to_list(length=1000)
    
    # Fix for legacy bets without new required fields
    fixed_bets = []
    for bet in bets:
        # Add default values for missing required fields
        if "side" not in bet:
            bet["side"] = "A"  # Default side
        if "event_id" not in bet:
            bet["event_id"] = f"legacy_{bet['id'][:8]}"  # Generate legacy event_id
        if "side_name" not in bet:
            bet["side_name"] = "Lado A"  # Default side name
        if "event_title" not in bet:
            bet["event_title"] = bet.get("event_description", "Evento Legacy")  # Use description as title
        
        try:
            fixed_bets.append(Bet(**bet))
        except Exception as e:
            print(f"❌ Failed to process bet {bet.get('id', 'unknown')}: {str(e)}")
    
    return fixed_bets

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
    fee = 0.0  # No fee for bet join
    net_amount = bet["amount"]
    
    transaction = Transaction(
        user_id=join_data.user_id,
        amount=bet["amount"],
        fee=fee,
        net_amount=net_amount,
        type=TransactionType.BET_DEBIT,
        status=TransactionStatus.APPROVED,
        description=f"Aposta aceita - {bet['event_description']}"
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

# Admin Payment Management Endpoints
@api_router.get("/admin/pending-deposits")
async def get_pending_deposits():
    """Get all pending deposit transactions for admin approval"""
    try:
        # Find all pending deposit transactions
        pending_deposits = await db.transactions.find({
            "status": TransactionStatus.PENDING,
            "type": TransactionType.DEPOSIT
        }).sort("created_at", -1).to_list(length=1000)
        
        # Enrich with user information
        enriched_deposits = []
        for deposit in pending_deposits:
            user = await db.users.find_one({"id": deposit["user_id"]})
            if user:
                enriched_deposit = {
                    "id": deposit["id"],
                    "user_id": deposit["user_id"],
                    "user_name": user["name"],
                    "user_email": user["email"],
                    "amount": deposit["amount"],
                    "fee": deposit.get("fee", 0.80),
                    "net_amount": deposit["amount"] - deposit.get("fee", 0.80),
                    "external_reference": deposit.get("external_reference", "N/A"),
                    "description": deposit.get("description", ""),
                    "created_at": deposit["created_at"],
                    "status": deposit["status"]
                }
                enriched_deposits.append(enriched_deposit)
        
        return {
            "pending_deposits": enriched_deposits,
            "total_count": len(enriched_deposits),
            "total_amount": sum(d["amount"] for d in enriched_deposits)
        }
        
    except Exception as e:
        print(f"❌ Error fetching pending deposits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending deposits: {str(e)}")

@api_router.post("/admin/approve-deposit/{transaction_id}")
async def admin_approve_deposit(transaction_id: str):
    """Manually approve a specific deposit transaction"""
    try:
        # Find the transaction
        transaction = await db.transactions.find_one({"id": transaction_id})
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        if transaction.get("status") == TransactionStatus.APPROVED:
            return {
                "message": "Deposit already approved", 
                "status": "already_approved",
                "transaction_id": transaction_id
            }
        
        # Get user info
        user = await db.users.find_one({"id": transaction["user_id"]})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        print(f"🔧 Admin manual approval for deposit: {transaction_id} - User: {user['name']}")
        
        # Update transaction to approved
        await db.transactions.update_one(
            {"id": transaction_id},
            {"$set": {
                "status": TransactionStatus.APPROVED,
                "updated_at": datetime.utcnow()
            }}
        )
        
        # Credit user balance
        fee = transaction.get("fee", 0.80)
        net_amount = transaction["amount"] - fee
        
        await db.users.update_one(
            {"id": transaction["user_id"]},
            {"$inc": {"balance": net_amount}}
        )
        
        # Get updated user balance
        updated_user = await db.users.find_one({"id": transaction["user_id"]})
        
        print(f"✅ Deposit approved: {transaction_id}, User: {user['name']}, Amount: R$ {transaction['amount']}, Net: R$ {net_amount}, New Balance: R$ {updated_user['balance']}")
        
        return {
            "transaction_id": transaction_id,
            "status": "approved",
            "message": f"Depósito aprovado com sucesso para {user['name']}",
            "user_name": user["name"],
            "user_email": user["email"],
            "amount": transaction["amount"],
            "fee": fee,
            "net_amount": net_amount,
            "new_user_balance": updated_user["balance"],
            "approval_time": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Admin approval error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to approve deposit: {str(e)}")

# Auto Payment Verification System
@api_router.post("/admin/auto-verify-payments")
async def auto_verify_pending_payments():
    """Automatically verify and process pending payments older than 5 minutes"""
    print("🔄 Auto-verifying pending payments older than 5 minutes")
    
    current_time = datetime.utcnow()
    five_minutes_ago = current_time - timedelta(minutes=5)
    
    # Find pending transactions older than 5 minutes
    pending_transactions = await db.transactions.find({
        "status": TransactionStatus.PENDING,
        "type": TransactionType.DEPOSIT,
        "created_at": {"$lt": five_minutes_ago}
    }).to_list(length=1000)
    
    processed_count = 0
    
    for transaction in pending_transactions:
        try:
            # Update transaction to approved
            await db.transactions.update_one(
                {"id": transaction["id"]},
                {"$set": {
                    "status": TransactionStatus.APPROVED,
                    "updated_at": current_time
                }}
            )
            
            # Credit user balance
            fee = transaction.get("fee", 0.80)
            net_amount = transaction["amount"] - fee
            await db.users.update_one(
                {"id": transaction["user_id"]},
                {"$inc": {"balance": net_amount}}
            )
            
            processed_count += 1
            print(f"✅ Auto-verified transaction {transaction['id']}, credited: R$ {net_amount}")
            
        except Exception as e:
            print(f"❌ Failed to auto-verify transaction {transaction['id']}: {str(e)}")
    
    return {
        "message": f"Auto-verified {processed_count} pending payments",
        "processed_count": processed_count,
        "auto_verification": True
    }

# Emergency Balance Fix Endpoint
@api_router.post("/admin/fix-pending-payments")
async def fix_pending_payments():
    """EMERGENCY: Fix all pending payments and restore user balances"""
    print("🚨 EMERGENCY: Starting balance fix for all pending payments")
    
    # Find all pending transactions
    pending_transactions = await db.transactions.find({
        "status": TransactionStatus.PENDING,
        "type": TransactionType.DEPOSIT
    }).to_list(length=1000)
    
    fixed_count = 0
    errors = []
    
    for transaction in pending_transactions:
        try:
            # Update transaction to approved
            await db.transactions.update_one(
                {"id": transaction["id"]},
                {"$set": {"status": TransactionStatus.APPROVED}}
            )
            
            # Credit user balance
            fee = transaction.get("fee", 0.80)  # Default AbacatePay fee if missing
            net_amount = transaction["amount"] - fee
            await db.users.update_one(
                {"id": transaction["user_id"]},
                {"$inc": {"balance": net_amount}}
            )
            
            fixed_count += 1
            print(f"✅ Fixed transaction {transaction['id']} for user {transaction['user_id']}, credited: R$ {net_amount}")
            
        except Exception as e:
            error_msg = f"Failed to fix transaction {transaction['id']}: {str(e)}"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
    
    return {
        "message": f"Emergency balance fix completed",
        "fixed_transactions": fixed_count,
        "errors": errors,
        "emergency_fix": True
    }

# Demo/Testing Endpoints
class DemoBalanceRequest(BaseModel):
    amount: float

@api_router.post("/demo/add-balance-v2/{user_id}")
async def demo_add_balance_v2(user_id: str, request: DemoBalanceRequest):
    """Demo endpoint to add balance to users for testing purposes (JSON body version)"""
    amount = request.amount
    
    # Check if user exists
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Add balance
    await db.users.update_one(
        {"id": user_id},
        {"$inc": {"balance": amount}}
    )
    
    # Create demo transaction record
    transaction = Transaction(
        user_id=user_id,
        amount=amount,
        fee=0.0,
        net_amount=amount,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.APPROVED,
        description=f"Demo balance added for testing: R$ {amount:.2f}"
    )
    await db.transactions.insert_one(transaction.dict())
    
    # Get updated user data
    updated_user = await db.users.find_one({"id": user_id})
    
    return {
        "message": f"Added R$ {amount:.2f} to user {user['name']}",
        "user_id": user_id,
        "user_name": user["name"],
        "previous_balance": user["balance"],
        "added_amount": amount,
        "new_balance": updated_user["balance"],
        "demo_mode": True
    }

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
        fee = 0.0  # No fee for refund
        net_amount = bet["amount"]
        
        refund_transaction = Transaction(
            user_id=bet["creator_id"],
            amount=bet["amount"],
            fee=fee,
            net_amount=net_amount,
            type=TransactionType.BET_CREDIT,  # Using bet_credit for refund
            status=TransactionStatus.APPROVED,
            description=f"Reembolso - aposta expirada: {bet['event_description']}"
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