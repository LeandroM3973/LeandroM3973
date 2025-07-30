import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Textarea } from './components/ui/textarea';
import { Trophy, Users, Target, DollarSign, Clock, CheckCircle } from 'lucide-react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [bets, setBets] = useState([]);
  const [waitingBets, setWaitingBets] = useState([]);
  const [userBets, setUserBets] = useState([]);
  const [userName, setUserName] = useState('');
  const [loading, setLoading] = useState(false);

  // Create Bet Form
  const [newBet, setNewBet] = useState({
    event_title: '',
    event_type: 'sports',
    event_description: '',
    amount: 100
  });

  // Judge Panel
  const [selectedBetForJudge, setSelectedBetForJudge] = useState(null);
  const [selectedWinner, setSelectedWinner] = useState('');

  useEffect(() => {
    loadUsers();
    loadBets();
    loadWaitingBets();
  }, []);

  useEffect(() => {
    if (currentUser) {
      loadUserBets();
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

  const createUser = async () => {
    if (!userName.trim()) return;
    setLoading(true);
    try {
      const response = await axios.post(`${API}/users`, { name: userName });
      setCurrentUser(response.data);
      setUserName('');
      await loadUsers();
    } catch (error) {
      console.error('Error creating user:', error);
    }
    setLoading(false);
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
        amount: 100
      });
      await Promise.all([loadBets(), loadWaitingBets(), loadUserBets()]);
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
      await Promise.all([loadBets(), loadWaitingBets(), loadUserBets()]);
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

  const getStatusColor = (status) => {
    switch (status) {
      case 'waiting': return 'bg-yellow-500';
      case 'active': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'waiting': return <Clock className="w-4 h-4" />;
      case 'active': return <Target className="w-4 h-4" />;
      case 'completed': return <CheckCircle className="w-4 h-4" />;
      default: return null;
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
            <p className="text-gray-300">Plataforma de Apostas com Eventos Externos</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Input
                placeholder="Digite seu nome"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                className="bg-white/10 border-white/20 text-white placeholder:text-gray-400"
                onKeyPress={(e) => e.key === 'Enter' && createUser()}
              />
            </div>
            <Button 
              onClick={createUser} 
              disabled={loading || !userName.trim()}
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            >
              {loading ? 'Criando...' : 'Entrar na Plataforma'}
            </Button>
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
              <span className="text-white font-semibold">{currentUser.balance} pontos</span>
            </div>
            <Button 
              variant="outline" 
              onClick={() => setCurrentUser(null)}
              className="border-white/20 text-white hover:bg-white/10"
            >
              Sair
            </Button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        <Tabs defaultValue="bets" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 bg-white/10 backdrop-blur-lg">
            <TabsTrigger value="bets" className="text-white data-[state=active]:bg-white/20">
              Apostas Disponíveis
            </TabsTrigger>
            <TabsTrigger value="create" className="text-white data-[state=active]:bg-white/20">
              Criar Aposta
            </TabsTrigger>
            <TabsTrigger value="my-bets" className="text-white data-[state=active]:bg-white/20">
              Minhas Apostas
            </TabsTrigger>
            <TabsTrigger value="judge" className="text-white data-[state=active]:bg-white/20">
              Painel do Juiz
            </TabsTrigger>
          </TabsList>

          {/* Available Bets */}
          <TabsContent value="bets">
            <div className="grid gap-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-white">Apostas Aguardando Adversário</h2>
                <Badge variant="outline" className="border-white/20 text-white">
                  {waitingBets.length} disponíveis
                </Badge>
              </div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {waitingBets.map((bet) => (
                  <Card key={bet.id} className="bg-white/10 backdrop-blur-lg border-white/20">
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <CardTitle className="text-white">{bet.event_title}</CardTitle>
                        <Badge className={`${getStatusColor(bet.status)} text-white`}>
                          <div className="flex items-center space-x-1">
                            {getStatusIcon(bet.status)}
                            <span>{bet.status}</span>
                          </div>
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <p className="text-gray-300 text-sm">{bet.event_description}</p>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Users className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-300 text-sm">vs {bet.creator_name}</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <DollarSign className="w-4 h-4 text-green-400" />
                          <span className="text-white font-semibold">{bet.amount} pontos</span>
                        </div>
                      </div>
                      <Badge variant="outline" className="border-white/20 text-white">
                        {bet.event_type}
                      </Badge>
                      {bet.creator_id !== currentUser.id && (
                        <Button 
                          onClick={() => joinBet(bet.id)}
                          disabled={loading || currentUser.balance < bet.amount}
                          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                        >
                          {loading ? 'Entrando...' : `Apostar ${bet.amount} pontos`}
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
              {waitingBets.length === 0 && (
                <div className="text-center py-12">
                  <Target className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-300">Nenhuma aposta disponível no momento</p>
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
                  <label className="text-white text-sm font-medium">Valor da Aposta (pontos)</label>
                  <Input
                    type="number"
                    value={newBet.amount}
                    onChange={(e) => setNewBet({...newBet, amount: parseInt(e.target.value) || 0})}
                    min="1"
                    max={currentUser.balance}
                    className="bg-white/10 border-white/20 text-white"
                  />
                </div>
                <Button 
                  onClick={createBet}
                  disabled={loading || !newBet.event_title.trim() || !newBet.event_description.trim() || newBet.amount > currentUser.balance}
                  className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                >
                  {loading ? 'Criando...' : 'Criar Aposta'}
                </Button>
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
                          <span className="text-white text-sm font-semibold">{bet.amount} pontos</span>
                        </div>
                        {bet.winner_name && (
                          <div className="flex justify-between">
                            <span className="text-gray-400 text-sm">Vencedor:</span>
                            <span className="text-green-400 text-sm font-semibold">{bet.winner_name}</span>
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
              {userBets.length === 0 && (
                <div className="text-center py-12">
                  <Trophy className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-300">Nenhuma aposta encontrada</p>
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
                          <span className="text-gray-400">Valor Total:</span>
                          <span className="text-green-400 font-semibold">{bet.amount * 2} pontos</span>
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