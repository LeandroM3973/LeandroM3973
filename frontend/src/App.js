import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Textarea } from './components/ui/textarea';
import { Trophy, Users, Target, DollarSign, Clock, CheckCircle, CreditCard, Wallet, ArrowUpCircle, ArrowDownCircle, History, Eye, EyeOff, Share2, Copy, Link } from 'lucide-react';
import axios from 'axios';
import './App.css';
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Remove AbacatePay SDK import - it's Node.js only and should only be used in backend
// Frontend will communicate with backend API for all payment operations
console.log('🥑 AbacatePay: Frontend configured to use backend API for payments');
const MP_PUBLIC_KEY = process.env.REACT_APP_MERCADO_PAGO_PUBLIC_KEY;

function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    // Try to load user from localStorage on app start
    const savedUser = localStorage.getItem('betarena_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [users, setUsers] = useState([]);
  const [bets, setBets] = useState([]);
  const [waitingBets, setWaitingBets] = useState([]);
  const [userBets, setUserBets] = useState([]);
  const [userTransactions, setUserTransactions] = useState([]);
  const [loading, setLoading] = useState(false);

  // Login/Register form
  const [authForm, setAuthForm] = useState({
    name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: ''
  });

  // Auth states
  const [isLogin, setIsLogin] = useState(true); // true = login, false = register
  const [emailVerificationRequired, setEmailVerificationRequired] = useState(false);
  const [verificationEmail, setVerificationEmail] = useState('');
  const [manualVerificationEmail, setManualVerificationEmail] = useState('');
  
  // Payment verification states
  const [paymentCheckLoading, setPaymentCheckLoading] = useState(false);
  const [lastPaymentTransactionId, setLastPaymentTransactionId] = useState('');
  const [emailExists, setEmailExists] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Create Bet Form
  const [newBet, setNewBet] = useState({
    event_title: '',
    event_type: 'sports',
    event_description: '',
    amount: 50.00
  });

  // Payment forms
  const [depositAmount, setDepositAmount] = useState(100.00);
  const [withdrawAmount, setWithdrawAmount] = useState(50.00);

  // Invite handling
  const [inviteCode, setInviteCode] = useState('');
  const [inviteBet, setInviteBet] = useState(null);
  const [inviteLoading, setInviteLoading] = useState(false);

  // Judge Panel
  const [selectedBetForJudge, setSelectedBetForJudge] = useState(null);
  const [selectedWinner, setSelectedWinner] = useState('');

  useEffect(() => {
    // Load user from localStorage on app initialization
    const savedUser = localStorage.getItem('betarena_user');
    if (savedUser) {
      try {
        const userData = JSON.parse(savedUser);
        setCurrentUser(userData);
        console.log('User loaded from localStorage:', userData.name);
      } catch (error) {
        console.error('Error parsing saved user data:', error);
        localStorage.removeItem('betarena_user');
      }
    }
    
    loadUsers();
    loadBets();
    loadWaitingBets();
    
    // Load user data if user is saved in localStorage
    if (currentUser) {
      loadUserBets();
      loadUserTransactions();
    }
  }, []);

  useEffect(() => {
    if (currentUser) {
      // Save user to localStorage whenever currentUser changes
      localStorage.setItem('betarena_user', JSON.stringify(currentUser));
      loadUserBets();
      loadUserTransactions();
    } else {
      // Remove user from localStorage when logged out
      localStorage.removeItem('betarena_user');
    }
  }, [currentUser]);

  const loadUsers = async () => {
    try {
      const response = await axios.get(`${API}/users`);
      setUsers(response.data);
    } catch (error) {
      console.error('Error loading users:', error);
    }
  };

  // Function to refresh current user data (for balance updates)
  const refreshCurrentUser = async () => {
    if (!currentUser) return;
    
    try {
      console.log('🔄 Refreshing user balance...');
      const response = await axios.get(`${API}/users/${currentUser.id}`);
      const updatedUser = response.data;
      
      setCurrentUser(updatedUser);
      localStorage.setItem('betarena_user', JSON.stringify(updatedUser));
      
      console.log(`💰 Balance updated: ${formatCurrency(updatedUser.balance)}`);
      return updatedUser;
    } catch (error) {
      console.error('Error refreshing user data:', error);
      return null;
    }
  };

  // Auto-refresh user data when window gains focus (user returns from payment)
  useEffect(() => {
    const handleWindowFocus = () => {
      if (currentUser) {
        console.log('👁️ Window focused, checking for balance updates...');
        
        // Check for pending payment
        const pendingPayment = localStorage.getItem('betarena_pending_payment');
        if (pendingPayment) {
          try {
            const paymentInfo = JSON.parse(pendingPayment);
            const timeDiff = Date.now() - paymentInfo.timestamp;
            
            // If payment was initiated less than 1 hour ago
            if (timeDiff < 3600000) {
              console.log('💳 Found pending payment, refreshing balance...');
              
              refreshCurrentUser().then((updatedUser) => {
                if (updatedUser) {
                  // Show success message if balance increased
                  setTimeout(() => {
                    alert(`💰 BEM-VINDO DE VOLTA!\n\n` +
                          `✅ Verificação de saldo concluída\n` +
                          `💳 Saldo atual: ${formatCurrency(updatedUser.balance)}\n\n` +
                          `Se você concluiu o pagamento, o saldo deve estar atualizado.`);
                  }, 1000);
                }
              });
              
              // Clear pending payment after 5 minutes to avoid repeated messages
              setTimeout(() => {
                localStorage.removeItem('betarena_pending_payment');
              }, 300000);
            } else {
              // Remove old pending payments
              localStorage.removeItem('betarena_pending_payment');
            }
          } catch (error) {
            localStorage.removeItem('betarena_pending_payment');
          }
        } else {
          refreshCurrentUser();
        }
      }
    };

    window.addEventListener('focus', handleWindowFocus);
    return () => window.removeEventListener('focus', handleWindowFocus);
  }, [currentUser]);

  // Set up periodic balance refresh every 30 seconds when user is active
  useEffect(() => {
    if (!currentUser) return;

    const balanceRefreshInterval = setInterval(() => {
      if (document.visibilityState === 'visible' && currentUser) {
        refreshCurrentUser();
      }
    }, 30000); // 30 seconds

    return () => clearInterval(balanceRefreshInterval);
  }, [currentUser]);

  const loadBets = async () => {
    try {
      const response = await axios.get(`${API}/bets`);
      setBets(response.data);
    } catch (error) {
      console.error('Error loading bets:', error);
    }
  };

  const loadWaitingBets = async () => {
    try {
      const response = await axios.get(`${API}/bets/waiting`);
      setWaitingBets(response.data);
    } catch (error) {
      console.error('Error loading waiting bets:', error);
    }
  };

  const loadUserBets = async () => {
    if (!currentUser) return;
    try {
      const response = await axios.get(`${API}/bets/user/${currentUser.id}`);
      setUserBets(response.data);
    } catch (error) {
      console.error('Error loading user bets:', error);
    }
  };

  const loadUserTransactions = async () => {
    if (!currentUser) return;
    try {
      const response = await axios.get(`${API}/transactions/${currentUser.id}`);
      setUserTransactions(response.data);
    } catch (error) {
      console.error('Error loading transactions:', error);
    }
  };

  const checkEmailExists = async (email) => {
    if (!email.trim() || !email.includes('@')) return;
    
    try {
      const response = await axios.post(`${API}/users/check-email`, null, {
        params: { email: email }
      });
      setEmailExists(response.data.exists);
      setIsLogin(response.data.exists);
    } catch (error) {
      console.error('Error checking email:', error);
      setEmailExists(false);
      setIsLogin(false);
    }
  };

  const handleAuth = async () => {
    if (!authForm.email.trim() || !authForm.password.trim()) {
      alert('Por favor, preencha email e senha');
      return;
    }
    
    if (isLogin) {
      // Login
      setLoading(true);
      try {
        const response = await axios.post(`${API}/users/login`, {
          email: authForm.email,
          password: authForm.password
        });
        setCurrentUser(response.data);
        setAuthForm({ name: '', email: '', phone: '', password: '', confirmPassword: '' });
        localStorage.setItem('betarena_user', JSON.stringify(response.data));
        console.log('✅ User logged in successfully:', response.data.name);
      } catch (error) {
        console.error('❌ Login error:', error);
        const errorMessage = error.response?.data?.detail;
        
        if (errorMessage && errorMessage.includes('não verificado')) {
          // Email not verified
          setEmailVerificationRequired(true);
          setVerificationEmail(authForm.email);
          alert(`📧 EMAIL NÃO VERIFICADO\n\n${errorMessage}\n\nPor favor, verifique seu email ou use a verificação manual temporária.`);
        } else if (errorMessage && errorMessage.includes('não encontrado')) {
          // Email not found  
          alert(`📧 EMAIL NÃO ENCONTRADO\n\n${errorMessage}\n\nVerifique se o email está correto ou crie uma nova conta.`);
        } else {
          // Other errors (wrong password, etc.)
          alert(errorMessage || 'Erro no login. Verifique suas credenciais.');
        }
      }
      setLoading(false);
    } else {
      // Register
      if (!authForm.name.trim() || !authForm.phone.trim()) {
        alert('Por favor, preencha todos os campos');
        return;
      }
      
      if (authForm.password !== authForm.confirmPassword) {
        alert('As senhas não coincidem');
        return;
      }
      
      if (authForm.password.length < 6) {
        alert('A senha deve ter pelo menos 6 caracteres');
        return;
      }
      
      setLoading(true);
      try {
        const response = await axios.post(`${API}/users`, {
          name: authForm.name,
          email: authForm.email,
          phone: authForm.phone,
          password: authForm.password
        });
        
        // Don't auto-login after registration - require email verification
        alert(`📧 CONTA CRIADA COM SUCESSO!\n\n` +
              `✅ Usuário: ${response.data.name}\n` +
              `📧 Email: ${authForm.email}\n\n` +
              `⚠️ IMPORTANTE: Seu email precisa ser verificado antes do primeiro login.\n\n` +
              `🔧 Use a verificação manual temporária abaixo para ativar sua conta.`);
        
        setEmailVerificationRequired(true);
        setVerificationEmail(authForm.email);
        setIsLogin(true); // Switch to login mode
        setAuthForm({ name: '', email: authForm.email, phone: '', password: '', confirmPassword: '' });
        console.log('📧 New user created (email verification required):', response.data.name);
      } catch (error) {
        console.error('❌ Registration error:', error);
        alert(error.response?.data?.detail || 'Erro ao criar conta');
      }
      setLoading(false);
    }
  };

  const handleEmailChange = (email) => {
    setAuthForm({...authForm, email: email});
    // Check if email exists after user stops typing
    const timeoutId = setTimeout(() => {
      checkEmailExists(email);
    }, 500);
    return () => clearTimeout(timeoutId);
  };

  const checkInviteCode = async () => {
    if (!inviteCode.trim()) {
      alert('Por favor, insira um código de convite');
      return;
    }
    
    setInviteLoading(true);
    try {
      const response = await axios.get(`${API}/bets/invite/${inviteCode.trim()}`);
      setInviteBet(response.data);
    } catch (error) {
      console.error('Error checking invite:', error);
      if (error.response?.status === 410) {
        alert('Este convite expirou');
      } else if (error.response?.status === 404) {
        alert('Código de convite não encontrado');
      } else if (error.response?.status === 400) {
        alert('Esta aposta não está mais disponível');
      } else {
        alert('Erro ao verificar convite');
      }
      setInviteBet(null);
    }
    setInviteLoading(false);
  };

  const joinBetByInvite = async () => {
    if (!inviteBet) return;
    
    setLoading(true);
    try {
      await axios.post(`${API}/bets/join-by-invite/${inviteCode.trim()}`, {
        user_id: currentUser.id
      });
      
      alert('Você entrou na aposta com sucesso!');
      setInviteCode('');
      setInviteBet(null);
      
      // Refresh data
      await Promise.all([loadUserBets(), loadUserTransactions()]);
      const userResponse = await axios.get(`${API}/users/${currentUser.id}`);
      setCurrentUser(userResponse.data);
      
    } catch (error) {
      console.error('Error joining bet by invite:', error);
      alert(error.response?.data?.detail || 'Erro ao entrar na aposta');
    }
    setLoading(false);
  };

  // Manual email verification function (temporary)
  const handleManualVerification = async () => {
    if (!manualVerificationEmail.trim()) {
      alert('Digite o email para verificação');
      return;
    }

    try {
      const response = await axios.post(`${API}/users/manual-verify?email=${encodeURIComponent(manualVerificationEmail)}`);
      alert(`✅ ${response.data.message}`);
      setEmailVerificationRequired(false);
      setManualVerificationEmail('');
      
      // If this was the verification email, clear it
      if (manualVerificationEmail === verificationEmail) {
        setVerificationEmail('');
      }
    } catch (error) {
      console.error('❌ Verification error:', error);
      alert(error.response?.data?.detail || 'Erro na verificação');
    }
  };

  const logout = () => {
    setCurrentUser(null);
    setAuthForm({ name: '', email: '', phone: '', password: '', confirmPassword: '' });
    setIsLogin(true);
    setEmailExists(false);
  };

  const createBet = async () => {
    if (!currentUser || !newBet.event_title.trim() || !newBet.event_description.trim()) return;
    setLoading(true);
    try {
      const betData = {
        ...newBet,
        creator_id: currentUser.id
      };
      await axios.post(`${API}/bets`, betData);
      setNewBet({
        event_title: '',
        event_type: 'sports',
        event_description: '',
        amount: 50.00
      });
      await Promise.all([loadBets(), loadWaitingBets(), loadUserBets(), loadUserTransactions()]);
      // Refresh current user balance
      const userResponse = await axios.get(`${API}/users/${currentUser.id}`);
      setCurrentUser(userResponse.data);
    } catch (error) {
      console.error('Error creating bet:', error);
      alert(error.response?.data?.detail || 'Error creating bet');
    }
    setLoading(false);
  };

  const joinBet = async (betId) => {
    if (!currentUser) return;
    setLoading(true);
    try {
      await axios.post(`${API}/bets/${betId}/join`, { user_id: currentUser.id });
      await Promise.all([loadBets(), loadWaitingBets(), loadUserBets(), loadUserTransactions()]);
      // Refresh current user balance
      const userResponse = await axios.get(`${API}/users/${currentUser.id}`);
      setCurrentUser(userResponse.data);
    } catch (error) {
      console.error('Error joining bet:', error);
      alert(error.response?.data?.detail || 'Error joining bet');
    }
    setLoading(false);
  };

  const declareWinner = async () => {
    if (!selectedBetForJudge || !selectedWinner) return;
    setLoading(true);
    try {
      await axios.post(`${API}/bets/${selectedBetForJudge.id}/declare-winner`, { 
        winner_id: selectedWinner 
      });
      setSelectedBetForJudge(null);
      setSelectedWinner('');
      await Promise.all([loadBets(), loadWaitingBets(), loadUserBets()]);
    } catch (error) {
      console.error('Error declaring winner:', error);
      alert(error.response?.data?.detail || 'Error declaring winner');
    }
    setLoading(false);
  };

  const handleDeposit = async () => {
    if (!currentUser || depositAmount < 10) return;
    setLoading(true);
    try {
      const response = await axios.post(`${API}/payments/create-preference`, {
        user_id: currentUser.id,
        amount: depositAmount
      });
      
      if (response.data.demo_mode) {
        // Show demo payment options
        const result = window.confirm(
          `💰 MODO DEMONSTRAÇÃO\n\n` +
          `Valor: ${formatCurrency(depositAmount)}\n` +
          `Transação: ${response.data.transaction_id}\n\n` +
          `Clique OK para SIMULAR PAGAMENTO APROVADO\n` +
          `Clique Cancelar para testar pagamento pendente`
        );
        
        if (result) {
          // Simulate approved payment
          const approvalResponse = await axios.post(`${API}/payments/simulate-approval/${response.data.transaction_id}`);
          alert(`✅ PAGAMENTO SIMULADO COM SUCESSO!\n\n${approvalResponse.data.message}\nValor: ${formatCurrency(approvalResponse.data.amount)}`);
          
          // Refresh user data
          const userResponse = await axios.get(`${API}/users/${currentUser.id}`);
          setCurrentUser(userResponse.data);
          await loadUserTransactions();
        } else {
          alert('💡 Pagamento deixado como pendente para demonstração.\nEm produção, o usuário seria redirecionado para o AbacatePay.');
        }
      } else if (response.data.abacatepay) {
        // AbacatePay payment flow with enhanced frontend integration
        const paymentUrl = response.data.payment_url || response.data.init_point;
        const billId = response.data.preference_id;
        
        console.log('🥑 AbacatePay Payment Data:', {
          billId,
          paymentUrl,
          amount: response.data.amount,
          fee: response.data.fee
        });
        
        // Detect if user is on mobile device (improved detection)
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || 
                         window.innerWidth <= 768 ||
                         'ontouchstart' in window ||
                         navigator.maxTouchPoints > 0;
        
        console.log(`📱 Device detection: isMobile=${isMobile}, userAgent=${navigator.userAgent}, width=${window.innerWidth}`);
        
        if (isMobile) {
          // Mobile-optimized flow with improved user experience
          try {
            const userChoice = window.confirm(
              `🥑 PAGAMENTO ABACATEPAY - MOBILE\n\n` +
              `Valor: ${formatCurrency(depositAmount)}\n` +
              `Taxa: R$ 0,80\n` +
              `Valor líquido: ${formatCurrency(depositAmount - 0.80)}\n\n` +
              `ID: ${billId}\n\n` +
              `📱 IMPORTANTE: Clique OK para abrir o pagamento PIX no seu celular.\n\n` +
              `✅ OK - Continuar com pagamento\n` +
              `❌ Cancelar - Voltar`
            );
            
            if (userChoice) {
              // Mobile-specific handling with multiple fallbacks
              console.log('📱 User confirmed mobile payment, redirecting...');
              
              // Try multiple mobile-friendly approaches
              try {
                // Method 1: Direct navigation (best for mobile)
                console.log('📱 Attempting direct navigation to:', paymentUrl);
                
                // Store payment info for balance refresh
                localStorage.setItem('betarena_pending_payment', JSON.stringify({
                  amount: depositAmount,
                  billId: billId,
                  timestamp: Date.now()
                }));
                
                // Show instruction about balance update
                alert(`💳 REDIRECIONANDO PARA PAGAMENTO PIX\n\n` +
                      `Após concluir o pagamento:\n` +
                      `✅ Retorne a este site\n` +
                      `✅ Seu saldo será atualizado automaticamente\n` +
                      `💰 Valor líquido: ${formatCurrency(depositAmount - 0.80)}\n\n` +
                      `ID: ${billId}`);
                
                window.location.href = paymentUrl;
              } catch (redirectError) {
                console.error('❌ Direct navigation failed:', redirectError);
                
                // Method 2: Fallback with user copy-paste option
                const fallbackChoice = window.confirm(
                  `🔗 ABRIR PAGAMENTO PIX\n\n` +
                  `Não foi possível abrir automaticamente.\n\n` +
                  `✅ Clique OK para copiar o link e abrir manualmente\n` +
                  `❌ Clique Cancelar para tentar novamente`
                );
                
                if (fallbackChoice) {
                  // Copy to clipboard and show instructions
                  if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(paymentUrl).then(() => {
                      alert(`📋 LINK COPIADO!\n\n${paymentUrl}\n\n📱 Cole este link no seu navegador para pagar.\n\nID: ${billId}`);
                    }).catch(() => {
                      // Show link for manual copy
                      alert(`🔗 LINK DE PAGAMENTO:\n\n${paymentUrl}\n\n📱 Copie e cole este link no seu navegador.\n\nID: ${billId}`);
                    });
                  } else {
                    alert(`🔗 LINK DE PAGAMENTO:\n\n${paymentUrl}\n\n📱 Copie e cole este link no seu navegador.\n\nID: ${billId}`);
                  }
                }
              }
            } else {
              console.log('📱 User cancelled mobile payment');
            }
          } catch (mobileError) {
            console.error('❌ Mobile payment error:', mobileError);
            alert(`❌ Erro no pagamento mobile: ${mobileError.message}\n\nTente novamente ou use um navegador diferente.`);
          }
        } else {
          // Desktop flow with popup handling
          const userChoice = window.confirm(
            `🥑 PAGAMENTO VIA ABACATEPAY\n\n` +
            `Valor: ${formatCurrency(depositAmount)}\n` +
            `Taxa: R$ 0,80\n` +
            `Valor líquido: ${formatCurrency(depositAmount - 0.80)}\n\n` +
            `Bill ID: ${billId}\n` +
            `Status: ${response.data.status}\n\n` +
            `✅ Clique OK para abrir o pagamento\n` +
            `❌ Clique Cancelar para desistir`
          );
          
          if (userChoice) {
            // Store payment info for balance refresh
            localStorage.setItem('betarena_pending_payment', JSON.stringify({
              amount: depositAmount,
              billId: billId,
              timestamp: Date.now()
            }));
            
            // Try window.open first on desktop
            const paymentWindow = window.open(paymentUrl, '_blank', 'noopener,noreferrer,width=800,height=600');
            
            // Check if popup was blocked after a short delay
            setTimeout(() => {
              if (!paymentWindow || paymentWindow.closed || typeof paymentWindow.closed == 'undefined') {
                // Popup was blocked - show fallback
                const fallbackChoice = window.confirm(
                  `🔒 POPUP BLOQUEADO\n\n` +
                  `Seu navegador bloqueou o popup do AbacatePay.\n\n` +
                  `✅ Clique OK para abrir na mesma aba\n` +
                  `❌ Clique Cancelar para copiar o link`
                );
                
                if (fallbackChoice) {
                  // Show balance update instruction
                  alert(`💳 ABRINDO PAGAMENTO PIX\n\n` +
                        `Após concluir o pagamento:\n` +
                        `✅ Retorne a este site\n` +
                        `✅ Seu saldo será atualizado automaticamente\n` +
                        `💰 Valor líquido: ${formatCurrency(depositAmount - 0.80)}\n\n` +
                        `ID: ${billId}`);
                  
                  // Navigate to payment page in same tab
                  window.location.href = paymentUrl;
                } else {
                  // Copy link to clipboard
                  navigator.clipboard.writeText(paymentUrl).then(() => {
                    alert(`🔗 LINK COPIADO!\n\n${paymentUrl}\n\n📋 Cole este link em uma nova aba para pagar no AbacatePay.\n\n💰 Após o pagamento, retorne aqui para ver seu saldo atualizado.\n\nBill ID: ${billId}`);
                  }).catch(() => {
                    alert(`🔗 LINK DE PAGAMENTO:\n\n${paymentUrl}\n\n📋 Copie este link e abra em uma nova aba.\n\n💰 Após o pagamento, retorne aqui para ver seu saldo atualizado.\n\nBill ID: ${billId}`);
                  });
                }
              } else {
                // Popup opened successfully
                alert(`🚀 Pagamento AbacatePay aberto!\n\n💳 Complete o pagamento PIX na nova janela.\n💰 Após o pagamento, retorne aqui para ver seu saldo atualizado automaticamente.\n\nBill ID: ${billId}`);
              }
            }, 1000);
          }
        }
      }
      
    } catch (error) {
      console.error('Error creating payment:', error);
      alert('Erro ao criar pagamento: ' + (error.response?.data?.detail || 'Erro desconhecido'));
    }
    setLoading(false);
  };

  const handleWithdraw = async () => {
    if (!currentUser || withdrawAmount <= 0 || withdrawAmount > currentUser.balance) return;
    setLoading(true);
    try {
      await axios.post(`${API}/payments/withdraw`, {
        user_id: currentUser.id,
        amount: withdrawAmount
      });
      
      alert('Solicitação de saque enviada! O valor será transferido para sua conta em até 24h.');
      
      // Refresh user data
      const userResponse = await axios.get(`${API}/users/${currentUser.id}`);
      setCurrentUser(userResponse.data);
      await loadUserTransactions();
      
    } catch (error) {
      console.error('Error processing withdrawal:', error);
      alert(error.response?.data?.detail || 'Erro ao processar saque');
    }
    setLoading(false);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'waiting': return 'bg-yellow-500';
      case 'active': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'approved': return 'bg-green-500';
      case 'pending': return 'bg-yellow-500';
      case 'rejected': return 'bg-red-500';
      case 'expired': return 'bg-gray-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'waiting': return <Clock className="w-4 h-4" />;
      case 'active': return <Target className="w-4 h-4" />;
      case 'completed': return <CheckCircle className="w-4 h-4" />;
      case 'approved': return <CheckCircle className="w-4 h-4" />;
      case 'pending': return <Clock className="w-4 h-4" />;
      case 'expired': return <Clock className="w-4 h-4" />;
      default: return null;
    }
  };

  const getTransactionIcon = (type) => {
    switch (type) {
      case 'deposit': return <ArrowDownCircle className="w-4 h-4 text-green-500" />;
      case 'withdrawal': return <ArrowUpCircle className="w-4 h-4 text-blue-500" />;
      case 'bet_debit': return <Target className="w-4 h-4 text-red-500" />;
      case 'bet_credit': return <Trophy className="w-4 h-4 text-green-500" />;
      default: return <History className="w-4 h-4" />;
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(amount);
  };

  const formatTimeRemaining = (expiresAt) => {
    const now = new Date();
    const expiry = new Date(expiresAt);
    const diff = expiry - now;
    
    if (diff <= 0) return "Expirada";
    
    const minutes = Math.floor(diff / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    if (minutes > 0) {
      return `${minutes}m ${seconds}s restantes`;
    } else {
      return `${seconds}s restantes`;
    }
  };

  const copyInviteLink = (inviteCode) => {
    const inviteUrl = `${window.location.origin}/invite/${inviteCode}`;
    navigator.clipboard.writeText(inviteUrl).then(() => {
      alert('🔗 Link de convite copiado!\n\nCompartilhe este link com seu adversário:\n' + inviteUrl);
    }).catch(() => {
      // Fallback for browsers that don't support clipboard API
      const textArea = document.createElement('textarea');
      textArea.value = inviteUrl;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      alert('🔗 Link de convite copiado!\n\nCompartilhe este link com seu adversário:\n' + inviteUrl);
    });
  };

  const shareInviteLink = (inviteCode) => {
    const inviteUrl = `${window.location.origin}/invite/${inviteCode}`;
    if (navigator.share) {
      navigator.share({
        title: 'Convite para Aposta - BetArena',
        text: `Você foi convidado para uma aposta! Valor: ${formatCurrency(userBets.find(bet => bet.invite_code === inviteCode)?.amount || 0)}`,
        url: inviteUrl,
      });
    } else {
      copyInviteLink(inviteCode);
    }
  };

  if (!currentUser) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-white/10 backdrop-blur-lg border-white/20">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mb-4">
              <Trophy className="w-8 h-8 text-white" />
            </div>
            <CardTitle className="text-2xl font-bold text-white">BetArena</CardTitle>
            <p className="text-gray-300">
              {isLogin ? 'Entre na sua conta' : 'Crie sua conta'}
            </p>
            <div className="mt-4 p-3 bg-blue-500/20 rounded-lg border border-blue-500/30">
              <p className="text-blue-200 text-sm">
                🛡️ <strong>Proteção Garantida:</strong> Protegemos seu dinheiro e garantimos que o valor seja entregue ao vencedor após o resultado final
              </p>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Input
                placeholder="Seu email"
                type="email"
                value={authForm.email}
                onChange={(e) => handleEmailChange(e.target.value)}
                className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                disabled={loading}
              />
              {emailExists && (
                <p className="text-green-400 text-sm mt-1">
                  ✓ Email encontrado - faça login
                </p>
              )}
              {authForm.email && !emailExists && !isLogin && (
                <p className="text-blue-400 text-sm mt-1">
                  ✓ Email disponível - criar nova conta
                </p>
              )}
            </div>
            
            <div className="relative">
              <Input
                placeholder="Sua senha"
                type={showPassword ? "text" : "password"}
                value={authForm.password}
                onChange={(e) => setAuthForm({...authForm, password: e.target.value})}
                className="bg-white/10 border-white/20 text-white placeholder:text-gray-400 pr-10"
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            
            {!isLogin && (
              <>
                <div>
                  <Input
                    placeholder="Confirme sua senha"
                    type={showPassword ? "text" : "password"}
                    value={authForm.confirmPassword}
                    onChange={(e) => setAuthForm({...authForm, confirmPassword: e.target.value})}
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                  />
                </div>
                <div>
                  <Input
                    placeholder="Nome completo"
                    value={authForm.name}
                    onChange={(e) => setAuthForm({...authForm, name: e.target.value})}
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                  />
                </div>
                <div>
                  <Input
                    placeholder="Telefone (11999999999)"
                    value={authForm.phone}
                    onChange={(e) => setAuthForm({...authForm, phone: e.target.value})}
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                  />
                </div>
              </>
            )}
            
            <Button 
              onClick={handleAuth} 
              disabled={loading || !authForm.email.trim() || !authForm.password.trim() || (!isLogin && (!authForm.name.trim() || !authForm.phone.trim() || authForm.password !== authForm.confirmPassword))}
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            >
              {loading ? 'Carregando...' : isLogin ? 'Entrar' : 'Criar Conta'}
            </Button>
            
            <div className="text-center">
              <button
                onClick={() => {
                  setIsLogin(!isLogin);
                  setAuthForm({ name: '', email: authForm.email, phone: '', password: '', confirmPassword: '' });
                }}
                className="text-sm text-gray-300 hover:text-white underline"
              >
                {isLogin ? 'Não tem conta? Criar nova conta' : 'Já tem conta? Fazer login'}
              </button>
            </div>
            
            {!authForm.email && (
              <p className="text-gray-400 text-sm text-center">
                Digite seu email para começar
              </p>
            )}
            
            {/* Email Verification Section */}
            {emailVerificationRequired && (
              <div className="mt-6 p-4 bg-yellow-500/20 rounded-lg border border-yellow-500/30">
                <div className="text-center mb-4">
                  <h3 className="text-lg font-bold text-yellow-200 mb-2">📧 Verificação de Email Necessária</h3>
                  {verificationEmail && (
                    <p className="text-yellow-200 text-sm mb-3">
                      Email pendente: <strong>{verificationEmail}</strong>
                    </p>
                  )}
                  <p className="text-yellow-200 text-sm">
                    ⚠️ Seu email precisa ser verificado para fazer login.
                  </p>
                </div>
                
                <div className="space-y-3">
                  <div>
                    <label className="block text-yellow-200 text-sm mb-1">
                      Verificação Manual (Temporária):
                    </label>
                    <div className="flex space-x-2">
                      <Input
                        placeholder="Digite seu email"
                        type="email"
                        value={manualVerificationEmail}
                        onChange={(e) => setManualVerificationEmail(e.target.value)}
                        className="flex-1 bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                      />
                      <button
                        onClick={handleManualVerification}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md text-sm font-medium transition-colors"
                      >
                        Verificar
                      </button>
                    </div>
                  </div>
                  
                  <div className="text-center">
                    <button
                      onClick={() => {
                        setEmailVerificationRequired(false);
                        setVerificationEmail('');
                        setManualVerificationEmail('');
                      }}
                      className="text-sm text-gray-300 hover:text-white underline"
                    >
                      Fechar verificação
                    </button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="bg-black/20 backdrop-blur-lg border-b border-white/10">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
              <Trophy className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">BetArena</h1>
              <p className="text-sm text-gray-300">Olá, {currentUser.name}</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 bg-white/10 rounded-lg px-4 py-2">
              <DollarSign className="w-5 h-5 text-green-400" />
              <span className="text-white font-semibold">{formatCurrency(currentUser.balance)}</span>
            </div>
            <Button 
              variant="outline" 
              onClick={logout}
              className="border-white/20 text-white hover:bg-white/10"
            >
              Sair
            </Button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <Tabs defaultValue="my-bets" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 md:grid-cols-6 bg-white/10 backdrop-blur-lg">
            <TabsTrigger value="my-bets" className="text-white data-[state=active]:bg-white/20 text-xs md:text-sm">
              <span className="hidden sm:inline">Minhas Apostas</span>
              <span className="sm:hidden">Apostas</span>
            </TabsTrigger>
            <TabsTrigger value="create" className="text-white data-[state=active]:bg-white/20 text-xs md:text-sm">
              <span className="hidden sm:inline">Criar Aposta</span>
              <span className="sm:hidden">Criar</span>
            </TabsTrigger>
            <TabsTrigger value="send-invite" className="text-white data-[state=active]:bg-white/20 text-xs md:text-sm">
              <span className="hidden sm:inline">Enviar Convite</span>
              <span className="sm:hidden">Convite</span>
            </TabsTrigger>
            <TabsTrigger value="payments" className="text-white data-[state=active]:bg-white/20 text-xs md:text-sm">
              <span className="hidden sm:inline">Pagamentos</span>
              <span className="sm:hidden">Pagar</span>
            </TabsTrigger>
            <TabsTrigger value="transactions" className="text-white data-[state=active]:bg-white/20 text-xs md:text-sm">
              <span className="hidden sm:inline">Histórico</span>
              <span className="sm:hidden">Histórico</span>
            </TabsTrigger>
            <TabsTrigger value="judge" className="text-white data-[state=active]:bg-white/20 text-xs md:text-sm">
              <span className="hidden sm:inline">Juiz</span>
              <span className="sm:hidden">Juiz</span>
            </TabsTrigger>
          </TabsList>

          {/* Security Notice */}
          <div className="bg-gradient-to-r from-green-500/20 to-blue-500/20 rounded-lg p-4 border border-green-500/30">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <div className="w-10 h-10 bg-green-500/30 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.031 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
              </div>
              <div className="flex-1">
                <h3 className="text-white font-semibold">Proteção Total dos Seus Recursos</h3>
                <p className="text-gray-300 text-sm mt-1">
                  A BetArena <strong>protege 100% do dinheiro apostado</strong> e garante que o valor seja <strong>automaticamente transferido ao vencedor</strong> após a declaração do resultado pelo juiz. Seu dinheiro está seguro conosco!
                </p>
              </div>
            </div>
          </div>

          {/* Send Invite */}
          <TabsContent value="send-invite">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-white">Enviar Convite de Aposta</h2>
              
              <div className="bg-gradient-to-r from-green-500/20 to-blue-500/20 rounded-lg p-4 border border-green-500/30">
                <div className="flex items-center space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-green-500/30 rounded-full flex items-center justify-center">
                      <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.031 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-white font-semibold">Garantia Total da BetArena</h3>
                    <p className="text-gray-300 text-sm mt-1">
                      Quando você cria uma aposta, <strong>seu dinheiro fica protegido e retido</strong> na plataforma até o resultado final. 
                      A BetArena <strong>garante que a parte vencedora será paga corretamente</strong> após a decisão do juiz. 
                      Zero risco de não receber!
                    </p>
                  </div>
                </div>
              </div>

              {/* Active Waiting Bets */}
              <div className="space-y-4">
                <h3 className="text-xl font-bold text-white">Suas Apostas Aguardando Adversário</h3>
                
                {userBets.filter(bet => bet.status === 'waiting' && bet.creator_id === currentUser.id).length > 0 ? (
                  <div className="grid gap-4">
                    {userBets.filter(bet => bet.status === 'waiting' && bet.creator_id === currentUser.id).map((bet) => (
                      <Card key={bet.id} className="bg-white/10 backdrop-blur-lg border-white/20">
                        <CardHeader>
                          <div className="flex justify-between items-start">
                            <div>
                              <CardTitle className="text-white text-lg">{bet.event_title}</CardTitle>
                              <p className="text-gray-300 text-sm mt-1">{bet.event_description}</p>
                            </div>
                            <Badge className="bg-yellow-500 text-white">
                              <Clock className="w-4 h-4 mr-1" />
                              Aguardando
                            </Badge>
                          </div>
                        </CardHeader>
                        
                        <CardContent className="space-y-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div className="text-center p-3 bg-white/5 rounded">
                              <DollarSign className="w-6 h-6 text-green-400 mx-auto mb-2" />
                              <p className="text-gray-400 text-sm">Valor Apostado</p>
                              <p className="text-white font-semibold">{formatCurrency(bet.amount)}</p>
                            </div>
                            
                            <div className="text-center p-3 bg-white/5 rounded">
                              <Trophy className="w-6 h-6 text-yellow-400 mx-auto mb-2" />
                              <p className="text-gray-400 text-sm">Prêmio para Vencedor</p>
                              <p className="text-white font-semibold">{formatCurrency(bet.amount * 2 * 0.80)}</p>
                            </div>
                          </div>

                          {/* Main Invite Link Section */}
                          <div className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-lg p-4 border border-blue-500/30">
                            <div className="text-center mb-4">
                              <h4 className="text-white font-semibold text-lg flex items-center justify-center">
                                🔗 Link de Convite Gerado
                              </h4>
                              <p className="text-blue-300 text-sm">Compartilhe este link com seu adversário</p>
                            </div>
                            
                            <div className="bg-black/30 rounded-lg p-3 mb-4">
                              <p className="text-white text-sm font-mono break-all text-center">
                                {`${window.location.origin}/invite/${bet.invite_code}`}
                              </p>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-3 mb-4">
                              <Button
                                onClick={() => copyInviteLink(bet.invite_code)}
                                className="bg-blue-600 hover:bg-blue-700 text-white"
                              >
                                <Copy className="w-4 h-4 mr-2" />
                                Copiar Link
                              </Button>
                              <Button
                                onClick={() => shareInviteLink(bet.invite_code)}
                                className="bg-green-600 hover:bg-green-700 text-white"
                              >
                                <Share2 className="w-4 h-4 mr-2" />
                                Compartilhar
                              </Button>
                            </div>
                            
                            <div className="bg-yellow-500/20 rounded-lg p-3 border border-yellow-500/30">
                              <h5 className="text-yellow-200 font-semibold text-sm mb-2">📱 Como Enviar o Convite:</h5>
                              <ul className="text-yellow-200 text-xs space-y-1">
                                <li>• <strong>WhatsApp:</strong> Cole o link na conversa</li>
                                <li>• <strong>Telegram:</strong> Envie o link diretamente</li>
                                <li>• <strong>SMS/Email:</strong> Compartilhe o link completo</li>
                                <li>• <strong>Presencial:</strong> Mostre o QR Code (se disponível)</li>
                              </ul>
                            </div>
                          </div>

                          {/* Security and Time Info */}
                          <div className="space-y-3">
                            <div className="bg-green-500/20 rounded-lg p-3 border border-green-500/30">
                              <p className="text-green-200 text-sm text-center">
                                🔒 <strong>Seu dinheiro está protegido:</strong> Os {formatCurrency(bet.amount)} ficam retidos na plataforma até o resultado final
                              </p>
                            </div>
                            
                            {bet.expires_at && (
                              <div className="bg-orange-500/20 rounded-lg p-3 border border-orange-500/30 text-center">
                                <p className="text-orange-200 text-sm">
                                  ⏰ <strong>Tempo restante:</strong> {formatTimeRemaining(bet.expires_at)}
                                </p>
                                <p className="text-orange-300 text-xs mt-1">
                                  Se ninguém aceitar, o valor será devolvido automaticamente
                                </p>
                              </div>
                            )}
                          </div>

                          <Badge variant="outline" className="border-white/20 text-white">
                            {bet.event_type}
                          </Badge>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <Card className="bg-white/10 backdrop-blur-lg border-white/20">
                    <CardContent className="text-center py-12">
                      <Link className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-white font-semibold mb-2">Nenhuma Aposta Aguardando</h3>
                      <p className="text-gray-300 mb-4">
                        Você não possui apostas aguardando adversário no momento.
                      </p>
                      <Button
                        onClick={() => document.querySelector('[data-state="inactive"][id*="create"]').click()}
                        className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                      >
                        Criar Nova Aposta
                      </Button>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* Instructions */}
              <div className="bg-blue-500/20 rounded-lg p-4 border border-blue-500/30">
                <h4 className="text-white font-semibold mb-3">💡 Como Funciona o Sistema de Convites</h4>
                <div className="space-y-2 text-blue-200 text-sm">
                  <p><strong>1. Você cria a aposta</strong> → Sistema gera link único automaticamente</p>
                  <p><strong>2. Compartilha o link</strong> → Adversário recebe todas as informações</p>
                  <p><strong>3. Adversário aceita</strong> → Ambos depósitos ficam protegidos na plataforma</p>
                  <p><strong>4. Vocês jogam/competem</strong> → Juiz assiste e declara o vencedor</p>
                  <p><strong>5. Pagamento automático</strong> → Vencedor recebe o prêmio na conta</p>
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Create Bet */}
          <TabsContent value="create">
            <Card className="bg-white/10 backdrop-blur-lg border-white/20">
              <CardHeader>
                <CardTitle className="text-white">Criar Nova Aposta</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-white text-sm font-medium">Título do Evento</label>
                  <Input
                    value={newBet.event_title}
                    onChange={(e) => setNewBet({...newBet, event_title: e.target.value})}
                    placeholder="Ex: Brasil vs Argentina - Copa do Mundo"
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                  />
                </div>
                <div>
                  <label className="text-white text-sm font-medium">Tipo de Evento</label>
                  <Select 
                    value={newBet.event_type} 
                    onValueChange={(value) => setNewBet({...newBet, event_type: value})}
                  >
                    <SelectTrigger className="bg-white/10 border-white/20 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="sports">Esportes</SelectItem>
                      <SelectItem value="stocks">Ações/Mercado</SelectItem>
                      <SelectItem value="custom">Personalizado</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-white text-sm font-medium">Descrição</label>
                  <Textarea
                    value={newBet.event_description}
                    onChange={(e) => setNewBet({...newBet, event_description: e.target.value})}
                    placeholder="Descreva os detalhes da aposta..."
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                  />
                </div>
                <div>
                  <label className="text-white text-sm font-medium">Valor da Aposta</label>
                  <Input
                    type="number"
                    step="0.01"
                    value={newBet.amount}
                    onChange={(e) => setNewBet({...newBet, amount: parseFloat(e.target.value) || 0})}
                    min="10"
                    max={currentUser.balance}
                    className="bg-white/10 border-white/20 text-white"
                  />
                  <p className="text-sm text-gray-400 mt-1">Mínimo: R$ 10,00 | Saldo: {formatCurrency(currentUser.balance)}</p>
                </div>
                <Button 
                  onClick={createBet}
                  disabled={loading || !newBet.event_title.trim() || !newBet.event_description.trim() || newBet.amount > currentUser.balance || newBet.amount < 10}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                >
                  {loading ? 'Criando...' : 'Criar Aposta'}
                </Button>
                
                <div className="bg-yellow-500/20 rounded-lg p-3 border border-yellow-500/30">
                  <p className="text-yellow-200 text-sm">
                    ⏰ <strong>Como Funciona:</strong> Após criar a aposta, você receberá um <strong>link completo</strong> para enviar ao seu adversário. 
                    O link contém todas as informações da aposta (valor, evento, seu nome). O adversário tem <strong>20 minutos</strong> para clicar no link e aceitar. 
                    Caso ninguém aceite, o valor será <strong>automaticamente devolvido</strong>.
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* User Bets */}
          <TabsContent value="my-bets">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-white">Minhas Apostas</h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {userBets.map((bet) => (
                  <Card key={bet.id} className="bg-white/10 backdrop-blur-lg border-white/20">
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <CardTitle className="text-white text-lg">{bet.event_title}</CardTitle>
                        <Badge className={`${getStatusColor(bet.status)} text-white`}>
                          <div className="flex items-center space-x-1">
                            {getStatusIcon(bet.status)}
                            <span>{bet.status}</span>
                          </div>
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-gray-300 text-sm">{bet.event_description}</p>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-gray-400 text-sm">Criador:</span>
                          <span className="text-white text-sm">{bet.creator_name}</span>
                        </div>
                        {bet.opponent_name && (
                          <div className="flex justify-between">
                            <span className="text-gray-400 text-sm">Oponente:</span>
                            <span className="text-white text-sm">{bet.opponent_name}</span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span className="text-gray-400 text-sm">Valor:</span>
                          <span className="text-white text-sm font-semibold">{formatCurrency(bet.amount)}</span>
                        </div>
                        {bet.winner_name && (
                          <div className="flex justify-between">
                            <span className="text-gray-400 text-sm">Vencedor:</span>
                            <span className="text-green-400 text-sm font-semibold">{bet.winner_name}</span>
                          </div>
                        )}
                        {bet.platform_fee && (
                          <>
                            <div className="flex justify-between">
                              <span className="text-gray-400 text-sm">Valor Total:</span>
                              <span className="text-white text-sm">{formatCurrency(bet.total_pot)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400 text-sm">Taxa Plataforma (20%):</span>
                              <span className="text-yellow-400 text-sm">-{formatCurrency(bet.platform_fee)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400 text-sm">Pagamento ao Vencedor:</span>
                              <span className="text-green-400 text-sm font-semibold">{formatCurrency(bet.winner_payout)}</span>
                            </div>
                          </>
                        )}
                      </div>
                      <Badge variant="outline" className="border-white/20 text-white">
                        {bet.event_type}
                      </Badge>
                      
                      {/* Invite Link Section for Waiting Bets */}
                      {bet.status === 'waiting' && bet.creator_id === currentUser.id && (
                        <div className="space-y-3">
                          <div className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-lg p-4 border border-blue-500/30">
                            <div className="flex items-center justify-between mb-3">
                              <div>
                                <p className="text-blue-200 font-semibold flex items-center">
                                  🔗 Link de Convite Gerado
                                </p>
                                <p className="text-blue-300 text-xs">Compartilhe com seu adversário</p>
                              </div>
                            </div>
                            
                            <div className="bg-white/10 rounded-lg p-3 mb-3">
                              <p className="text-white text-sm font-mono break-all">
                                {`${window.location.origin}/invite/${bet.invite_code}`}
                              </p>
                            </div>
                            
                            <div className="flex space-x-2">
                              <Button
                                size="sm"
                                onClick={() => copyInviteLink(bet.invite_code)}
                                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                              >
                                <Copy className="w-4 h-4 mr-2" />
                                Copiar Link
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => shareInviteLink(bet.invite_code)}
                                className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                              >
                                <Share2 className="w-4 h-4 mr-2" />
                                Compartilhar
                              </Button>
                            </div>
                            
                            <div className="mt-3 p-2 bg-yellow-500/20 rounded text-xs text-yellow-200">
                              💡 <strong>Como usar:</strong> Envie este link por WhatsApp, Telegram ou qualquer mensageiro. 
                              Seu adversário clicará no link e verá todos os detalhes da aposta antes de aceitar.
                            </div>
                          </div>
                          
                          {bet.expires_at && (
                            <div className="bg-orange-500/20 rounded p-3 text-center border border-orange-500/30">
                              <p className="text-orange-200 text-sm">
                                ⏰ <strong>Tempo restante:</strong> {formatTimeRemaining(bet.expires_at)}
                              </p>
                              <p className="text-orange-300 text-xs mt-1">
                                Se ninguém aceitar o convite, o valor será devolvido automaticamente
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
              {userBets.length === 0 && (
                <div className="text-center py-12">
                  <Trophy className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-300">Nenhuma aposta encontrada</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Payments */}
          <TabsContent value="payments">
            <div className="grid md:grid-cols-2 gap-6">
              {/* Deposit */}
              <Card className="bg-white/10 backdrop-blur-lg border-white/20">
                <CardHeader>
                  <CardTitle className="text-white flex items-center space-x-2">
                    <ArrowDownCircle className="w-6 h-6 text-green-400" />
                    <span>Depositar</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-white text-sm font-medium">Valor do Depósito</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={depositAmount}
                      onChange={(e) => setDepositAmount(parseFloat(e.target.value) || 0)}
                      min="10"
                      className="bg-white/10 border-white/20 text-white"
                    />
                    <p className="text-sm text-gray-400 mt-1">Mínimo: R$ 10,00</p>
                  </div>
                  <div className="bg-white/5 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">🛡️ Proteção BetArena:</h4>
                    <div className="space-y-2 text-sm text-gray-300">
                      <p>• <strong>Dinheiro protegido:</strong> Valores ficam seguros na plataforma</p>
                      <p>• <strong>Transferência garantida:</strong> Pagamento automático ao vencedor</p>
                      <p>• <strong>Zero risco de perda:</strong> Seu dinheiro está 100% seguro</p>
                    </div>
                  </div>
                  <Button 
                    onClick={handleDeposit}
                    disabled={loading || depositAmount < 10}
                    className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
                  >
                    {loading ? 'Processando...' : `Depositar ${formatCurrency(depositAmount)}`}
                  </Button>
                </CardContent>
              </Card>

              {/* Withdraw */}
              <Card className="bg-white/10 backdrop-blur-lg border-white/20">
                <CardHeader>
                  <CardTitle className="text-white flex items-center space-x-2">
                    <ArrowUpCircle className="w-6 h-6 text-blue-400" />
                    <span>Sacar</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-white text-sm font-medium">Valor do Saque</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={withdrawAmount}
                      onChange={(e) => setWithdrawAmount(parseFloat(e.target.value) || 0)}
                      min="10"
                      max={currentUser.balance}
                      className="bg-white/10 border-white/20 text-white"
                    />
                    <p className="text-sm text-gray-400 mt-1">
                      Disponível: {formatCurrency(currentUser.balance)}
                    </p>
                  </div>
                  <div className="bg-white/5 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">Informações:</h4>
                    <div className="space-y-1 text-sm text-gray-300">
                      <p>• Transferência via PIX</p>
                      <p>• Processamento em até 24h</p>
                    </div>
                  </div>
                  <Button 
                    onClick={handleWithdraw}
                    disabled={loading || withdrawAmount <= 0 || withdrawAmount > currentUser.balance}
                    className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                  >
                    {loading ? 'Processando...' : `Sacar ${formatCurrency(withdrawAmount)}`}
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Transactions */}
          <TabsContent value="transactions">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-white">Histórico de Transações</h2>
              <div className="space-y-3">
                {userTransactions.map((tx) => (
                  <Card key={tx.id} className="bg-white/10 backdrop-blur-lg border-white/20">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          {getTransactionIcon(tx.type)}
                          <div>
                            <p className="text-white font-medium">
                              {tx.type === 'deposit' && 'Depósito'}
                              {tx.type === 'withdrawal' && 'Saque'}
                              {tx.type === 'bet_debit' && 'Aposta Criada/Entrada'}
                              {tx.type === 'bet_credit' && 'Vitória em Aposta'}
                            </p>
                            <p className="text-gray-400 text-sm">
                              {new Date(tx.created_at).toLocaleString('pt-BR')}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className={`font-semibold ${
                            tx.type === 'deposit' || tx.type === 'bet_credit' ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {tx.type === 'deposit' || tx.type === 'bet_credit' ? '+' : '-'}
                            {formatCurrency(tx.amount)}
                          </p>
                          <Badge className={`${getStatusColor(tx.status)} text-white text-xs`}>
                            {tx.status}
                          </Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
              {userTransactions.length === 0 && (
                <div className="text-center py-12">
                  <History className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-300">Nenhuma transação encontrada</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Judge Panel */}
          <TabsContent value="judge">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-white">Painel do Juiz</h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {bets.filter(bet => bet.status === 'active').map((bet) => (
                  <Card key={bet.id} className="bg-white/10 backdrop-blur-lg border-white/20">
                    <CardHeader>
                      <CardTitle className="text-white">{bet.event_title}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <p className="text-gray-300 text-sm">{bet.event_description}</p>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-gray-400">Participantes:</span>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="text-center p-2 bg-white/5 rounded">
                            <p className="text-white font-medium">{bet.creator_name}</p>
                          </div>
                          <div className="text-center p-2 bg-white/5 rounded">
                            <p className="text-white font-medium">{bet.opponent_name}</p>
                          </div>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Valor Total do Prêmio:</span>
                          <span className="text-green-400 font-semibold">{formatCurrency(bet.amount * 2)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-500">Taxa da plataforma (20%):</span>
                          <span className="text-yellow-400">-{formatCurrency(bet.amount * 2 * 0.20)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-400">Pagamento ao Vencedor:</span>
                          <span className="text-green-400 font-semibold">{formatCurrency(bet.amount * 2 * 0.80)}</span>
                        </div>
                        <div className="mt-3 p-2 bg-blue-500/20 rounded text-xs text-blue-200">
                          <strong>🔒 Proteção Garantida:</strong> O valor fica protegido na plataforma até a decisão final
                        </div>
                      </div>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button 
                            className="w-full bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700"
                            onClick={() => setSelectedBetForJudge(bet)}
                          >
                            Declarar Vencedor
                          </Button>
                        </DialogTrigger>
                        <DialogContent className="bg-slate-900 border-slate-700">
                          <DialogHeader>
                            <DialogTitle className="text-white">Declarar Vencedor</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4">
                            <p className="text-gray-300">{selectedBetForJudge?.event_title}</p>
                            <Select value={selectedWinner} onValueChange={setSelectedWinner}>
                              <SelectTrigger className="bg-white/10 border-white/20 text-white">
                                <SelectValue placeholder="Selecione o vencedor" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value={selectedBetForJudge?.creator_id}>
                                  {selectedBetForJudge?.creator_name}
                                </SelectItem>
                                <SelectItem value={selectedBetForJudge?.opponent_id}>
                                  {selectedBetForJudge?.opponent_name}
                                </SelectItem>
                              </SelectContent>
                            </Select>
                            <Button 
                              onClick={declareWinner}
                              disabled={loading || !selectedWinner}
                              className="w-full bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700"
                            >
                              {loading ? 'Processando...' : 'Confirmar Vencedor'}
                            </Button>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </CardContent>
                  </Card>
                ))}
              </div>
              {bets.filter(bet => bet.status === 'active').length === 0 && (
                <div className="text-center py-12">
                  <CheckCircle className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-300">Nenhuma aposta ativa para julgar</p>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default App;