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
  const [pendingDeposits, setPendingDeposits] = useState([]); // New state for admin
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

  // Create Bet Form - Enhanced for automatic matching
  const [newBet, setNewBet] = useState({
    event_title: '',
    event_type: 'sports',
    event_description: '',
    amount: 50.00,
    event_id: '',  // For matching bets (e.g., "brasil_vs_argentina")
    side: 'A',     // "A" or "B"  
    side_name: ''  // Human readable (e.g., "Brasil", "Argentina")
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

  // Auto refresh user balance every 30 seconds
  useEffect(() => {
    if (!currentUser) return;
    
    const balanceCheckInterval = setInterval(async () => {
      try {
        const response = await axios.get(`${API}/users/${currentUser.id}`);
        const serverBalance = response.data.balance;
        
        // Check if balance changed
        if (Math.abs(serverBalance - currentUser.balance) > 0.01) {
          console.log(`💰 Balance update detected: ${formatCurrency(currentUser.balance)} → ${formatCurrency(serverBalance)}`);
          
          // Show notification to user
          if (serverBalance > currentUser.balance) {
            const difference = serverBalance - currentUser.balance;
            alert(`💰 SEU SALDO FOI ATUALIZADO!\n\n` +
                  `💎 Valor creditado: ${formatCurrency(difference)}\n` +
                  `💳 Saldo anterior: ${formatCurrency(currentUser.balance)}\n` +
                  `💳 Novo saldo: ${formatCurrency(serverBalance)}\n\n` +
                  `✅ Seu depósito foi aprovado pelo administrador!`);
          }
          
          // Update current user data
          await refreshCurrentUser();
        }
      } catch (error) {
        console.error('Error checking balance updates:', error);
      }
    }, 30000); // Check every 30 seconds
    
    return () => clearInterval(balanceCheckInterval);
  }, [currentUser]);

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
      // Load pending deposits if user is admin
      if (currentUser.is_admin) {
        loadPendingDeposits();
      }
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

  // Function to refresh current user data (for balance updates and admin status)
  const refreshCurrentUser = async () => {
    if (!currentUser) return;
    
    try {
      console.log('🔄 Refreshing user data and admin status...');
      const response = await axios.get(`${API}/users/${currentUser.id}`);
      const updatedUser = response.data;
      
      // Also check admin status to ensure it's current
      try {
        const adminCheck = await axios.get(`${API}/admin/check-admin/${currentUser.id}`);
        if (adminCheck.data) {
          updatedUser.is_admin = adminCheck.data.is_admin;
          console.log(`🔒 Admin status updated: ${updatedUser.is_admin ? 'ADMIN' : 'Regular User'}`);
        }
      } catch (adminError) {
        console.log('⚠️ Could not check admin status:', adminError.message);
      }
      
      setCurrentUser(updatedUser);
      localStorage.setItem('betarena_user', JSON.stringify(updatedUser));
      
      console.log(`💰 User refreshed: ${updatedUser.name} (Admin: ${updatedUser.is_admin ? 'Yes' : 'No'})`);
      console.log(`💰 Balance: ${formatCurrency(updatedUser.balance)}`);
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
        
        // Get fresh user data including admin status
        const userData = response.data;
        
        // Force refresh of user data to get latest admin status
        console.log('🔄 Refreshing user data to get latest admin status...');
        const refreshedUser = await refreshCurrentUser() || userData;
        
        setCurrentUser(refreshedUser);
        setAuthForm({ name: '', email: '', phone: '', password: '', confirmPassword: '' });
        localStorage.setItem('betarena_user', JSON.stringify(refreshedUser));
        
        if (refreshedUser.is_admin) {
          console.log('✅ Admin user logged in:', refreshedUser.name);
          console.log('🔒 Admin privileges active');
        } else {
          console.log('✅ Regular user logged in:', refreshedUser.name);
        }
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

  // Check payment status function
  const checkPaymentStatus = async (transactionId) => {
    if (!transactionId) {
      alert('ID da transação não disponível');
      return;
    }

    setPaymentCheckLoading(true);
    try {
      console.log(`🔍 Verificando status do pagamento: ${transactionId}`);
      const response = await axios.post(`${API}/payments/check-status/${transactionId}`);
      
      const result = response.data;
      console.log('💳 Status do pagamento:', result);

      if (result.balance_updated) {
        // Refresh user data to show updated balance
        await refreshCurrentUser();
        
        alert(`✅ PAGAMENTO CONFIRMADO!\n\n` +
              `💰 Status: ${result.status}\n` +
              `✅ ${result.message}\n\n` +
              `Seu saldo foi atualizado automaticamente!`);
      } else {
        alert(`⏳ PAGAMENTO PENDENTE\n\n` +
              `📋 Status: ${result.status}\n` +
              `💬 ${result.message}\n\n` +
              `Continue verificando até o pagamento ser confirmado.`);
      }
    } catch (error) {
      console.error('❌ Erro ao verificar pagamento:', error);
      alert(error.response?.data?.detail || 'Erro ao verificar status do pagamento');
    } finally {
      setPaymentCheckLoading(false);
    }
  };

  // Force refresh user data
  const forceRefreshUserData = async () => {
    setLoading(true);
    try {
      console.log('🔄 Force refreshing user data...');
      
      await Promise.all([
        refreshCurrentUser(),
        loadUserBets(),
        loadUserTransactions()
      ]);
      
      alert('✅ DADOS ATUALIZADOS!\n\nSeus dados foram recarregados com sucesso.');
      
    } catch (error) {
      console.error('Error force refreshing user data:', error);
      alert('❌ Erro ao atualizar dados. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  // Load pending deposits for admin
  const loadPendingDeposits = async () => {
    if (!currentUser?.is_admin) return;
    
    try {
      const response = await axios.get(`${API}/admin/pending-deposits`);
      setPendingDeposits(response.data.pending_deposits || []);
      console.log('📋 Loaded pending deposits:', response.data);
    } catch (error) {
      console.error('Error loading pending deposits:', error);
    }
  };

  // Manually approve deposit
  const approveDeposit = async (transactionId, userName) => {
    if (!currentUser?.is_admin) {
      alert('❌ Apenas administradores podem aprovar depósitos');
      return;
    }
    
    if (window.confirm(`✅ APROVAR DEPÓSITO\n\nDeseja aprovar o depósito de ${userName}?\n\nTransação: ${transactionId}\n\n⚠️ Esta ação creditará o saldo do usuário.`)) {
      try {
        setLoading(true);
        console.log(`🔧 Aprovando depósito: ${transactionId}`);
        
        const response = await axios.post(`${API}/admin/approve-deposit/${transactionId}`);
        const result = response.data;
        
        console.log('✅ Depósito aprovado:', result);
        
        alert(`✅ DEPÓSITO APROVADO COM SUCESSO!\n\n` +
              `👤 Usuário: ${result.user_name}\n` +
              `💰 Valor: R$ ${result.amount.toFixed(2)}\n` +
              `💸 Taxa: R$ ${result.fee.toFixed(2)}\n` +
              `💎 Valor líquido: R$ ${result.net_amount.toFixed(2)}\n` +
              `💳 Saldo atual: R$ ${result.new_user_balance.toFixed(2)}\n\n` +
              `${result.message}\n\n` +
              `ℹ️ O usuário será notificado automaticamente em até 30 segundos, ou pode usar o botão "🔄 Atualizar" para ver o saldo imediatamente.`);
        
        // Reload pending deposits and user data
        await Promise.all([
          loadPendingDeposits(),
          loadUsers(),
          loadUserTransactions()
        ]);
        
        if (currentUser) {
          await refreshCurrentUser();
        }
        
      } catch (error) {
        console.error('❌ Erro ao aprovar depósito:', error);
        const errorMsg = error.response?.data?.detail || 'Erro ao aprovar depósito';
        alert(`❌ ERRO NA APROVAÇÃO\n\n${errorMsg}`);
      } finally {
        setLoading(false);
      }
    }
  };

  // Auto verify pending payments function
  const autoVerifyPendingPayments = async () => {
    try {
      setLoading(true);
      console.log('🔄 Verificando pagamentos pendentes automaticamente...');
      
      const response = await axios.post(`${API}/admin/auto-verify-payments`);
      const result = response.data;
      
      console.log('✅ Verificação automática concluída:', result);
      
      if (result.processed_count > 0) {
        alert(`✅ VERIFICAÇÃO AUTOMÁTICA CONCLUÍDA!\n\n` +
              `🔄 Processados: ${result.processed_count} pagamentos\n` +
              `💰 Saldos dos usuários foram atualizados automaticamente!\n\n` +
              `Recarregue a página para ver as atualizações.`);
              
        // Reload data
        await Promise.all([loadUsers(), loadBets(), loadUserBets(), loadUserTransactions()]);
        if (currentUser) {
          await refreshCurrentUser();
          // Reload pending deposits if admin
          if (currentUser.is_admin) {
            await loadPendingDeposits();
          }
        }
      } else {
        alert(`ℹ️ VERIFICAÇÃO CONCLUÍDA\n\nNenhum pagamento pendente foi encontrado para processar.`);
      }
      
    } catch (error) {
      console.error('❌ Erro na verificação automática:', error);
      alert(error.response?.data?.detail || 'Erro na verificação automática de pagamentos');
    } finally {
      setLoading(false);
    }
  };

  // Manual payment approval function (for testing)
  const manualApprovePayment = async (transactionId, amount) => {
    if (!transactionId || !amount) {
      alert('Dados do pagamento não disponíveis');
      return;
    }

    if (window.confirm(`🔧 APROVAÇÃO MANUAL\n\nDeseja aprovar manualmente o pagamento?\n\nTransação: ${transactionId}\nValor: R$ ${amount.toFixed(2)}\n\n⚠️ Use apenas para testes!`)) {
      try {
        console.log(`🔧 Aprovação manual: ${transactionId}, R$ ${amount}`);
        const response = await axios.post(`${API}/payments/manual-approve/${transactionId}?amount=${amount}`);
        
        const result = response.data;
        console.log('✅ Pagamento aprovado manualmente:', result);

        // Refresh user data
        await refreshCurrentUser();
        
        alert(`✅ PAGAMENTO APROVADO MANUALMENTE!\n\n` +
              `💰 Valor: R$ ${result.amount}\n` +
              `💸 Taxa: R$ ${result.fee}\n` +
              `💎 Valor líquido: R$ ${result.net_amount}\n\n` +
              `${result.message}`);
              
      } catch (error) {
        console.error('❌ Erro na aprovação manual:', error);
        alert(error.response?.data?.detail || 'Erro na aprovação manual');
      }
    }
  };

  const logout = () => {
    setCurrentUser(null);
    setAuthForm({ name: '', email: '', phone: '', password: '', confirmPassword: '' });
    setIsLogin(true);
    setEmailExists(false);
  };

  const createBet = async () => {
    console.log('🎯 Starting createBet function');
    console.log('Current user:', currentUser);
    console.log('New bet data:', newBet);
    
    if (!currentUser || !newBet.event_title.trim() || !newBet.event_description.trim() || !newBet.event_id.trim() || !newBet.side_name.trim()) {
      console.log('❌ Validation failed:', {
        hasUser: !!currentUser,
        hasTitle: !!newBet.event_title.trim(),
        hasDescription: !!newBet.event_description.trim(),
        hasEventId: !!newBet.event_id.trim(),
        hasSideName: !!newBet.side_name.trim()
      });
      alert('⚠️ Por favor, preencha todos os campos obrigatórios');
      return;
    }
    
    setLoading(true);
    try {
      const betData = {
        event_title: newBet.event_title,
        event_type: newBet.event_type,
        event_description: newBet.event_description,
        amount: newBet.amount,
        creator_id: currentUser.id,
        event_id: newBet.event_id,
        side: newBet.side,
        side_name: newBet.side_name
      };
      
      console.log('🎯 Creating bet with matching system:', betData);
      
      const response = await axios.post(`${API}/bets`, betData);
      
      console.log('✅ Bet creation response:', response.data);
      
      // Check if bet was automatically matched
      if (response.data.status === 'active') {
        alert(`🎉 APOSTA CONECTADA AUTOMATICAMENTE!\n\n` +
              `Sua aposta em "${newBet.side_name}" foi conectada com uma aposta oposta!\n\n` +
              `Aguarde o administrador decidir o vencedor.`);
      } else {
        alert(`⏳ APOSTA CRIADA COM SUCESSO!\n\n` +
              `Sua aposta em "${newBet.side_name}" está aguardando uma aposta oposta.\n\n` +
              `Quando alguém apostar no lado oposto, as apostas serão conectadas automaticamente.`);
      }
      
      setNewBet({
        event_title: '',
        event_type: 'sports', 
        event_description: '',
        amount: 50.00,
        event_id: '',
        side: 'A',
        side_name: ''
      });
      
      await Promise.all([loadBets(), loadWaitingBets(), loadUserBets(), loadUserTransactions()]);
      
      // Refresh current user balance
      await refreshCurrentUser();
      
    } catch (error) {
      console.error('❌ Error creating bet - Full error object:', error);
      console.error('❌ Error response:', error.response);
      console.error('❌ Error response data:', error.response?.data);
      
      // Handle different error types more carefully
      let errorMessage = 'Erro ao criar aposta';
      
      if (error.response?.data?.detail) {
        // Handle string or object detail
        const detail = error.response.data.detail;
        console.log('❌ Error detail type:', typeof detail);
        console.log('❌ Error detail value:', detail);
        
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map(err => typeof err === 'string' ? err : JSON.stringify(err)).join('\n');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      console.log('❌ Final error message:', errorMessage);
      alert(errorMessage);
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
    
    // Verify admin access
    if (!currentUser?.is_admin) {
      alert('❌ ACESSO NEGADO\n\nApenas administradores podem declarar vencedores.');
      return;
    }
    
    setLoading(true);
    try {
      await axios.post(`${API}/bets/${selectedBetForJudge.id}/declare-winner`, { 
        winner_id: selectedWinner,
        admin_user_id: currentUser.id  // Include admin user ID for verification
      });
      
      alert(`✅ VENCEDOR DECLARADO!\n\nVencedor: ${selectedWinner === selectedBetForJudge.creator_id ? selectedBetForJudge.creator_name : selectedBetForJudge.opponent_name}\n\nO saldo foi transferido automaticamente.`);
      
      setSelectedBetForJudge(null);
      setSelectedWinner('');
      await Promise.all([loadBets(), loadWaitingBets(), loadUserBets()]);
    } catch (error) {
      console.error('Error declaring winner:', error);
      const errorMsg = error.response?.data?.detail || 'Erro ao declarar vencedor';
      alert(`❌ ERRO AO DECLARAR VENCEDOR\n\n${errorMsg}`);
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
        const transactionId = response.data.transaction_id;
        
        // Save transaction ID for later status checking
        setLastPaymentTransactionId(transactionId);
        
        console.log('🥑 AbacatePay Payment Data:', {
          billId,
          paymentUrl,
          transactionId,
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
      
      // Handle different error types more carefully
      let errorMessage = 'Erro ao criar pagamento';
      
      if (error.response?.data?.detail) {
        // Handle string or object detail
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail)) {
          errorMessage = detail.map(err => typeof err === 'string' ? err : JSON.stringify(err)).join('\n');
        } else if (typeof detail === 'object') {
          errorMessage = JSON.stringify(detail);
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert('Erro ao criar pagamento: ' + errorMessage);
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
        <div className="container mx-auto px-4 py-4">
          {/* Desktop Layout */}
          <div className="hidden md:flex justify-between items-center">
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
                <span className="text-white font-semibold flex items-center space-x-2">
                  <span>{formatCurrency(currentUser.balance)}</span>
                  {currentUser.is_admin && (
                    <span className="inline-flex items-center px-2 py-1 bg-yellow-500/80 text-yellow-100 text-xs font-bold rounded-full">
                      🔒 ADMIN
                    </span>
                  )}
                </span>
              </div>
              <Button 
                onClick={forceRefreshUserData}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-3 py-1"
                size="sm"
              >
                {loading ? '⏳' : '🔄 Atualizar'}
              </Button>
              <Button 
                variant="outline" 
                onClick={logout}
                className="border-white/20 text-white hover:bg-white/10"
              >
                Sair
              </Button>
            </div>
          </div>

          {/* Mobile Layout */}
          <div className="md:hidden">
            {/* Mobile Header Row 1 - Logo and User */}
            <div className="flex justify-between items-center mb-3">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                  <Trophy className="w-4 h-4 text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-white">BetArena</h1>
                  <p className="text-xs text-gray-300">Olá, {currentUser.name}</p>
                </div>
              </div>
              
              {/* Mobile Admin Badge */}
              {currentUser.is_admin && (
                <span className="inline-flex items-center px-2 py-1 bg-yellow-500/80 text-yellow-100 text-xs font-bold rounded-full">
                  🔒 ADMIN
                </span>
              )}
            </div>

            {/* Mobile Header Row 2 - Balance and Actions */}
            <div className="flex justify-between items-center">
              {/* Balance Display - Mobile Optimized */}
              <div className="flex items-center space-x-2 bg-white/10 rounded-lg px-3 py-2 flex-1 mr-2">
                <DollarSign className="w-4 h-4 text-green-400" />
                <span className="text-white font-semibold text-sm">
                  {formatCurrency(currentUser.balance)}
                </span>
              </div>
              
              {/* Action Buttons - Mobile Optimized */}
              <div className="flex items-center space-x-2">
                <Button 
                  onClick={forceRefreshUserData}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-2 py-1"
                  size="sm"
                >
                  {loading ? '⏳' : '🔄'}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={logout}
                  className="border-white/20 text-white hover:bg-white/10 text-xs px-3 py-1"
                  size="sm"
                >
                  Sair
                </Button>
              </div>
            </div>
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
            {/* Judge tab - ADMIN ONLY */}
            {currentUser?.is_admin && (
              <TabsTrigger value="judge" className="text-white data-[state=active]:bg-white/20 text-xs md:text-sm">
                <span className="hidden sm:inline">🔒 Juiz</span>
                <span className="sm:hidden">🔒 Juiz</span>
              </TabsTrigger>
            )}
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
                            
                            <div className="flex flex-col sm:flex-row gap-3 mb-4">
                              <Button
                                onClick={() => copyInviteLink(bet.invite_code)}
                                className="bg-blue-600 hover:bg-blue-700 text-white"
                              >
                                <Copy className="w-4 h-4 mr-2" />
                                <span className="hidden sm:inline">Copiar Link</span>
                                <span className="sm:hidden">Copiar</span>
                              </Button>
                              <Button
                                onClick={() => shareInviteLink(bet.invite_code)}
                                className="bg-green-600 hover:bg-green-700 text-white"
                              >
                                <Share2 className="w-4 h-4 mr-2" />
                                <span className="hidden sm:inline">Compartilhar</span>
                                <span className="sm:hidden">Enviar</span>
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

          {/* Create Bet - Enhanced with Auto-Matching */}
          <TabsContent value="create">
            <Card className="bg-white/10 backdrop-blur-lg border-white/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center space-x-2">
                  🎯 <span>Criar Aposta com Matching Automático</span>
                </CardTitle>
                <p className="text-gray-300 text-sm">
                  Sistema conecta automaticamente apostas opostas do mesmo evento
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                
                {/* Event ID for Matching */}
                <div>
                  <label className="text-white text-sm font-medium">ID do Evento (para conexão automática)</label>
                  <Input
                    value={newBet.event_id}
                    onChange={(e) => setNewBet({...newBet, event_id: e.target.value})}
                    placeholder="Ex: brasil_vs_argentina_final"
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                  />
                  <p className="text-gray-400 text-xs mt-1">
                    Use o mesmo ID para apostas que devem se conectar
                  </p>
                </div>

                {/* Event Title */}
                <div>
                  <label className="text-white text-sm font-medium">Título do Evento</label>
                  <Input
                    value={newBet.event_title}
                    onChange={(e) => setNewBet({...newBet, event_title: e.target.value})}
                    placeholder="Ex: Brasil vs Argentina - Copa do Mundo"
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                  />
                  <p className="text-gray-400 text-xs mt-1">
                    Título público do evento
                  </p>
                </div>

                {/* Event Description */}
                <div>
                  <label className="text-white text-sm font-medium">Descrição do Evento</label>
                  <Input
                    value={newBet.event_description}
                    onChange={(e) => setNewBet({...newBet, event_description: e.target.value})}
                    placeholder="Ex: Final da Copa - Brasil vs Argentina"
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                  />
                </div>

                {/* Side Selection */}
                <div>
                  <label className="text-white text-sm font-medium">Escolha seu lado</label>
                  <div className="flex space-x-4 mt-2">
                    <Button
                      type="button"
                      variant={newBet.side === 'A' ? 'default' : 'outline'}
                      className={`flex-1 ${newBet.side === 'A' ? 'bg-blue-600 hover:bg-blue-700' : 'border-white/20 text-white hover:bg-white/10'}`}
                      onClick={() => setNewBet({...newBet, side: 'A'})}
                    >
                      Lado A
                    </Button>
                    <Button
                      type="button"
                      variant={newBet.side === 'B' ? 'default' : 'outline'}
                      className={`flex-1 ${newBet.side === 'B' ? 'bg-green-600 hover:bg-green-700' : 'border-white/20 text-white hover:bg-white/10'}`}
                      onClick={() => setNewBet({...newBet, side: 'B'})}
                    >
                      Lado B
                    </Button>
                  </div>
                </div>

                {/* Side Name */}
                <div>
                  <label className="text-white text-sm font-medium">
                    Nome do seu lado ({newBet.side === 'A' ? 'Lado A' : 'Lado B'})
                  </label>
                  <Input
                    value={newBet.side_name}
                    onChange={(e) => setNewBet({...newBet, side_name: e.target.value})}
                    placeholder={newBet.side === 'A' ? "Ex: Brasil" : "Ex: Argentina"}
                    className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                  />
                </div>

                {/* Bet Amount */}
                <div>
                  <label className="text-white text-sm font-medium">Valor da Aposta</label>
                  <Input
                    type="number"
                    value={newBet.amount}
                    onChange={(e) => setNewBet({...newBet, amount: parseFloat(e.target.value)})}
                    min="1"
                    step="0.01"
                    className="bg-white/10 border-white/20 text-white"
                  />
                  <p className="text-gray-400 text-xs mt-1">
                    Mínimo: R$ 1,00
                  </p>
                </div>

                {/* Example/Preview */}
                {newBet.event_title && newBet.event_id && newBet.side_name && (
                  <div className="bg-green-500/20 rounded-lg p-4 border border-green-500/30">
                    <h4 className="text-green-200 font-semibold mb-2">📋 Preview da Aposta</h4>
                    <div className="space-y-1 text-sm text-green-200">
                      <p><strong>Título:</strong> {newBet.event_title}</p>
                      <p><strong>ID Evento:</strong> {newBet.event_id}</p>
                      <p><strong>Seu lado:</strong> {newBet.side_name} ({newBet.side})</p>
                      <p><strong>Valor:</strong> {formatCurrency(newBet.amount)}</p>
                      <p><strong>Buscando:</strong> Aposta oposta no mesmo evento</p>
                    </div>
                  </div>
                )}

                <Button
                  onClick={createBet}
                  disabled={loading || !currentUser}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                >
                  {loading ? 'Criando Aposta...' : '🎯 Criar Aposta (Auto-Match)'}
                </Button>
              </CardContent>
            </Card>

            {/* Auto-Matching Instructions */}
            <div className="mt-6 bg-blue-500/20 rounded-lg p-4 border border-blue-500/30">
              <h4 className="text-white font-semibold mb-3">🎯 Como Funciona o Sistema Automático</h4>
              <div className="space-y-2 text-blue-200 text-sm">
                <p><strong>1. João aposta no Brasil</strong> → Aposta fica aguardando</p>
                <p><strong>2. Maria aposta na Argentina</strong> → Sistema conecta automaticamente!</p>
                <p><strong>3. Apostas ficam ativas</strong> → Aguardando decisão do administrador</p>
                <p><strong>4. Admin decide vencedor</strong> → Pagamento automático (80% vencedor + 20% taxa)</p>
              </div>
            </div>
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
                            
                            <div className="flex flex-col sm:flex-row gap-2">
                              <Button
                                size="sm"
                                onClick={() => copyInviteLink(bet.invite_code)}
                                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
                              >
                                <Copy className="w-4 h-4 mr-2" />
                                <span className="hidden sm:inline">Copiar Link</span>
                                <span className="sm:hidden">Copiar</span>
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => shareInviteLink(bet.invite_code)}
                                className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                              >
                                <Share2 className="w-4 h-4 mr-2" />
                                <span className="hidden sm:inline">Compartilhar</span>
                                <span className="sm:hidden">Enviar</span>
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
                    className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-sm py-3 font-medium"
                  >
                    {loading ? 'Processando...' : `💳 Depositar ${formatCurrency(depositAmount)}`}
                  </Button>
                </CardContent>
              </Card>

              {/* Payment Status Check */}
              {lastPaymentTransactionId && (
                <Card className="bg-white/10 backdrop-blur-lg border-white/20">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center space-x-2">
                      <CheckCircle className="w-6 h-6 text-yellow-400" />
                      <span>Verificar Pagamento</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="bg-yellow-500/20 rounded-lg p-4 border border-yellow-500/30">
                      <p className="text-yellow-200 text-sm mb-2">
                        <strong>💳 Último Pagamento:</strong>
                      </p>
                      <p className="text-white text-xs font-mono mb-3">
                        ID: {lastPaymentTransactionId}
                      </p>
                      <p className="text-yellow-200 text-xs mb-4">
                        ⚠️ O webhook automático pode não estar funcionando. Use os botões abaixo para verificar se seu pagamento foi processado.
                      </p>
                      
                      <div className="space-y-2">
                        <Button
                          onClick={() => checkPaymentStatus(lastPaymentTransactionId)}
                          disabled={paymentCheckLoading}
                          className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                        >
                          {paymentCheckLoading ? 'Verificando...' : '🔍 Verificar Status do Pagamento'}
                        </Button>
                        
                        <Button
                          onClick={() => manualApprovePayment(lastPaymentTransactionId, depositAmount)}
                          className="w-full bg-orange-600 hover:bg-orange-700 text-white text-sm"
                        >
                          🔧 Aprovar Manualmente (Teste)
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

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

          {/* Judge Panel - ADMIN ONLY */}
          {currentUser?.is_admin && (
            <TabsContent value="judge">
              <div className="space-y-6">
                  <div className="bg-white/10 backdrop-blur-lg border-white/20 rounded-lg p-6">
                  <h2 className="text-2xl font-bold text-white flex items-center space-x-2 mb-4">
                    🔒 <span>Painel do Juiz (Administrador)</span>
                  </h2>
                  <p className="text-gray-300 mb-6">
                    ⚠️ <strong>Acesso restrito ao administrador.</strong> Apenas você pode declarar vencedores das apostas.
                  </p>
                  
                  {/* Admin Tools */}
                  <div className="bg-red-500/20 rounded-lg p-4 border border-red-500/30 mb-6">
                    <h3 className="text-red-200 font-semibold mb-2">🚨 Ferramentas de Emergência</h3>
                    <div className="flex flex-wrap gap-4">
                      <Button
                        onClick={autoVerifyPendingPayments}
                        disabled={loading}
                        className="bg-yellow-600 hover:bg-yellow-700 text-white"
                      >
                        {loading ? 'Verificando...' : '🔄 Verificar Pagamentos Pendentes'}
                      </Button>
                      <Button
                        onClick={loadPendingDeposits}
                        disabled={loading}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        {loading ? 'Carregando...' : '🔄 Atualizar Lista'}
                      </Button>
                    </div>
                    <p className="text-red-200 text-xs mt-2">
                      Use apenas se houver problemas com webhooks de pagamento
                    </p>
                  </div>

                  {/* Pending Deposits Management */}
                  <div className="bg-orange-500/20 rounded-lg p-6 border border-orange-500/30 mb-6">
                    <h3 className="text-orange-200 font-semibold mb-4 flex items-center space-x-2">
                      💰 <span>Aprovação Manual de Depósitos</span>
                      <Badge className="bg-orange-600 text-white">
                        {pendingDeposits.length} pendentes
                      </Badge>
                    </h3>
                    
                    <p className="text-orange-200 text-sm mb-4">
                      ℹ️ Aprove manualmente os depósitos após confirmar o pagamento no AbacatePay
                    </p>
                    
                    {pendingDeposits.length > 0 ? (
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {pendingDeposits.map((deposit) => (
                          <Card key={deposit.id} className="bg-white/10 backdrop-blur-lg border-orange-500/30">
                            <CardContent className="p-4">
                              <div className="flex items-center justify-between">
                                <div className="flex-1">
                                  <div className="flex items-center space-x-3 mb-2">
                                    <div className="bg-orange-600 p-2 rounded-full">
                                      <DollarSign className="w-4 h-4 text-white" />
                                    </div>
                                    <div>
                                      <p className="text-white font-semibold">{deposit.user_name}</p>
                                      <p className="text-gray-300 text-sm">{deposit.user_email}</p>
                                    </div>
                                  </div>
                                  
                                  <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                      <p className="text-gray-400">Valor Bruto:</p>
                                      <p className="text-orange-200 font-medium">R$ {deposit.amount.toFixed(2)}</p>
                                    </div>
                                    <div>
                                      <p className="text-gray-400">Valor Líquido:</p>
                                      <p className="text-green-200 font-medium">R$ {deposit.net_amount.toFixed(2)}</p>
                                    </div>
                                    <div>
                                      <p className="text-gray-400">Taxa:</p>
                                      <p className="text-red-200 font-medium">R$ {deposit.fee.toFixed(2)}</p>
                                    </div>
                                    <div>
                                      <p className="text-gray-400">Data:</p>
                                      <p className="text-gray-200 font-medium">
                                        {new Date(deposit.created_at).toLocaleString('pt-BR')}
                                      </p>
                                    </div>
                                  </div>
                                  
                                  {deposit.external_reference !== 'N/A' && (
                                    <div className="mt-2">
                                      <p className="text-gray-400 text-xs">ID AbacatePay:</p>
                                      <p className="text-gray-200 text-xs font-mono break-all">
                                        {deposit.external_reference}
                                      </p>
                                    </div>
                                  )}
                                </div>
                                
                                <div className="ml-4">
                                  <Button
                                    onClick={() => approveDeposit(deposit.id, deposit.user_name)}
                                    disabled={loading}
                                    className="bg-green-600 hover:bg-green-700 text-white"
                                    size="sm"
                                  >
                                    {loading ? '⏳' : '✅ Aprovar'}
                                  </Button>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8">
                        <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-2" />
                        <p className="text-orange-200">Nenhum depósito pendente</p>
                        <p className="text-orange-300 text-sm">Todos os depósitos foram processados!</p>
                      </div>
                    )}
                  </div>
                </div>
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
          )}
        </Tabs>
      </div>
    </div>
  );
}

export default App;