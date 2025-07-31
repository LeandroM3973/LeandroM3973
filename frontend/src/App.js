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
        console.log('User logged in:', response.data.name);
      } catch (error) {
        console.error('Error logging in:', error);
        alert(error.response?.data?.detail || 'Email ou senha incorretos');
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
        setCurrentUser(response.data);
        setAuthForm({ name: '', email: '', phone: '', password: '', confirmPassword: '' });
        await loadUsers();
        console.log('New user created:', response.data.name);
      } catch (error) {
        console.error('Error creating user:', error);
        alert(error.response?.data?.detail || 'Erro ao criar usuário');
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
          alert('💡 Pagamento deixado como pendente para demonstração.\nEm produção, o usuário seria redirecionado para o Mercado Pago.');
        }
      } else {
        // Redirect to real Mercado Pago (when using real keys)
        window.open(response.data.sandbox_init_point, '_blank');
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
          <TabsList className="grid w-full grid-cols-6 bg-white/10 backdrop-blur-lg">
            <TabsTrigger value="my-bets" className="text-white data-[state=active]:bg-white/20">
              Minhas Apostas
            </TabsTrigger>
            <TabsTrigger value="create" className="text-white data-[state=active]:bg-white/20">
              Criar Aposta
            </TabsTrigger>
            <TabsTrigger value="join-invite" className="text-white data-[state=active]:bg-white/20">
              Aceitar Convite
            </TabsTrigger>
            <TabsTrigger value="payments" className="text-white data-[state=active]:bg-white/20">
              Pagamentos
            </TabsTrigger>
            <TabsTrigger value="transactions" className="text-white data-[state=active]:bg-white/20">
              Histórico
            </TabsTrigger>
            <TabsTrigger value="judge" className="text-white data-[state=active]:bg-white/20">
              Juiz
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

          {/* Join by Invite */}
          <TabsContent value="join-invite">
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-white">Aceitar Convite de Aposta</h2>
              
              <Card className="bg-white/10 backdrop-blur-lg border-white/20">
                <CardHeader>
                  <CardTitle className="text-white flex items-center space-x-2">
                    <Link className="w-6 h-6" />
                    <span>Código de Convite</span>
                  </CardTitle>
                  <p className="text-gray-300 text-sm">
                    Cole aqui o código de convite que você recebeu para participar de uma aposta
                  </p>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex space-x-2">
                    <Input
                      placeholder="Ex: abc12345"
                      value={inviteCode}
                      onChange={(e) => setInviteCode(e.target.value)}
                      className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                      onKeyPress={(e) => e.key === 'Enter' && checkInviteCode()}
                    />
                    <Button 
                      onClick={checkInviteCode}
                      disabled={inviteLoading || !inviteCode.trim()}
                      className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700"
                    >
                      {inviteLoading ? 'Verificando...' : 'Verificar'}
                    </Button>
                  </div>
                  
                  <div className="bg-blue-500/20 rounded-lg p-3 border border-blue-500/30">
                    <p className="text-blue-200 text-sm">
                      💡 <strong>Como funciona:</strong> Cole o código de 8 caracteres que você recebeu via WhatsApp, 
                      Telegram ou outro meio. Exemplo: <code className="bg-white/20 px-1 rounded">abc12345</code>
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Invite Bet Details */}
              {inviteBet && (
                <Card className="bg-white/10 backdrop-blur-lg border-white/20">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-white">Detalhes da Aposta</CardTitle>
                      <Badge className="bg-yellow-500 text-white">
                        <Clock className="w-4 h-4 mr-1" />
                        Aguardando
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <h3 className="text-lg font-bold text-white">{inviteBet.event_title}</h3>
                      <p className="text-gray-300 text-sm">{inviteBet.event_description}</p>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div className="text-center p-3 bg-white/5 rounded">
                        <Users className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                        <p className="text-gray-400 text-sm">Adversário</p>
                        <p className="text-white font-semibold">{inviteBet.creator_name}</p>
                      </div>
                      
                      <div className="text-center p-3 bg-white/5 rounded">
                        <DollarSign className="w-6 h-6 text-green-400 mx-auto mb-2" />
                        <p className="text-gray-400 text-sm">Valor para Depositar</p>
                        <p className="text-white font-semibold text-lg">{formatCurrency(inviteBet.amount)}</p>
                      </div>
                    </div>

                    <div className="bg-orange-500/20 rounded-lg p-3 border border-orange-500/30">
                      <p className="text-orange-200 text-sm text-center">
                        ⏰ <strong>Tempo restante:</strong> {formatTimeRemaining(inviteBet.expires_at)}
                      </p>
                    </div>

                    {/* Prize Information */}
                    <div className="bg-green-500/20 rounded-lg p-4 border border-green-500/30">
                      <h4 className="text-white font-semibold mb-2">💰 Informações do Prêmio</h4>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-300">Valor total do pote:</span>
                          <span className="text-white font-semibold">{formatCurrency(inviteBet.amount * 2)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Taxa da plataforma (20%):</span>
                          <span className="text-yellow-400">-{formatCurrency(inviteBet.amount * 2 * 0.20)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-300">Prêmio para o vencedor:</span>
                          <span className="text-green-400 font-semibold">{formatCurrency(inviteBet.amount * 2 * 0.80)}</span>
                        </div>
                      </div>
                    </div>

                    <Badge variant="outline" className="border-white/20 text-white">
                      {inviteBet.event_type}
                    </Badge>

                    {/* Action Buttons */}
                    <div className="space-y-3">
                      {currentUser.balance >= inviteBet.amount ? (
                        <Button 
                          onClick={joinBetByInvite}
                          disabled={loading}
                          className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-lg py-3"
                        >
                          {loading ? 'Entrando na Aposta...' : `Aceitar Convite - Depositar ${formatCurrency(inviteBet.amount)}`}
                        </Button>
                      ) : (
                        <div className="space-y-2">
                          <Button 
                            disabled
                            className="w-full bg-gray-600 text-lg py-3"
                          >
                            Saldo Insuficiente
                          </Button>
                          <p className="text-center text-red-400 text-sm">
                            Você precisa de {formatCurrency(inviteBet.amount)} para aceitar este convite
                          </p>
                        </div>
                      )}
                      
                      <Button 
                        onClick={() => {
                          setInviteCode('');
                          setInviteBet(null);
                        }}
                        variant="outline"
                        className="w-full border-white/20 text-white hover:bg-white/10"
                      >
                        Cancelar
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {!inviteBet && (
                <div className="text-center py-12">
                  <Link className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-300">Digite um código de convite para ver os detalhes da aposta</p>
                </div>
              )}
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
                    ⏰ <strong>Tempo Limite:</strong> Após criar a aposta, você terá um <strong>link de convite</strong> para compartilhar. O adversário tem <strong>20 minutos</strong> para aceitar e depositar. Caso ninguém participe, o valor será <strong>automaticamente devolvido</strong> para sua conta.
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
                        <div className="space-y-2">
                          <div className="bg-blue-500/20 rounded-lg p-3 border border-blue-500/30">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-blue-200 text-sm font-medium">🔗 Link de Convite</p>
                                <p className="text-blue-300 text-xs">Compartilhe com seu adversário</p>
                              </div>
                              <div className="flex space-x-2">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => copyInviteLink(bet.invite_code)}
                                  className="border-blue-400/30 text-blue-200 hover:bg-blue-500/20"
                                >
                                  <Copy className="w-4 h-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => shareInviteLink(bet.invite_code)}
                                  className="border-blue-400/30 text-blue-200 hover:bg-blue-500/20"
                                >
                                  <Share2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          </div>
                          
                          {bet.expires_at && (
                            <div className="bg-orange-500/20 rounded p-2 text-xs text-orange-200 text-center">
                              ⏰ {formatTimeRemaining(bet.expires_at)}
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