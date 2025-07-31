import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Trophy, DollarSign, Clock, Users, Target } from 'lucide-react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function InvitePage() {
  const { inviteCode } = useParams();
  const navigate = useNavigate();
  const [bet, setBet] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    loadBetByInvite();
    loadCurrentUser();
  }, [inviteCode]);

  const loadCurrentUser = () => {
    const savedUser = localStorage.getItem('betarena_user');
    if (savedUser) {
      setCurrentUser(JSON.parse(savedUser));
    }
  };

  const loadBetByInvite = async () => {
    try {
      const response = await axios.get(`${API}/bets/invite/${inviteCode}`);
      setBet(response.data);
      setError(null);
    } catch (err) {
      if (err.response?.status === 410) {
        setError('Este convite expirou');
      } else if (err.response?.status === 404) {
        setError('Convite não encontrado');
      } else if (err.response?.status === 400) {
        setError('Esta aposta não está mais disponível');
      } else {
        setError('Erro ao carregar convite');
      }
    }
    setLoading(false);
  };

  const joinBet = async () => {
    if (!currentUser) {
      alert('Você precisa estar logado para aceitar o convite');
      navigate('/');
      return;
    }

    setJoining(true);
    try {
      await axios.post(`${API}/bets/join-by-invite/${inviteCode}`, {
        user_id: currentUser.id
      });
      
      alert('Você entrou na aposta com sucesso! Redirecionando...');
      navigate('/');
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao entrar na aposta');
    }
    setJoining(false);
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
    
    if (diff <= 0) return "Expirado";
    
    const minutes = Math.floor(diff / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    if (minutes > 0) {
      return `${minutes}m ${seconds}s restantes`;
    } else {
      return `${seconds}s restantes`;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-white text-lg">Carregando convite...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-white/10 backdrop-blur-lg border-white/20">
          <CardHeader className="text-center">
            <div className="mx-auto w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mb-4">
              <Trophy className="w-8 h-8 text-red-400" />
            </div>
            <CardTitle className="text-2xl font-bold text-white">Convite Inválido</CardTitle>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-gray-300">{error}</p>
            <Button 
              onClick={() => navigate('/')}
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            >
              Voltar ao Início
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl bg-white/10 backdrop-blur-lg border-white/20">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mb-4">
            <Trophy className="w-8 h-8 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold text-white">Convite para Aposta</CardTitle>
          <p className="text-gray-300">Você foi convidado para participar desta aposta!</p>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Bet Details */}
          <div className="bg-white/5 rounded-lg p-4 space-y-4">
            <div className="flex justify-between items-start">
              <h3 className="text-xl font-bold text-white">{bet.event_title}</h3>
              <Badge className="bg-yellow-500 text-white">
                <Clock className="w-4 h-4 mr-1" />
                Aguardando
              </Badge>
            </div>
            
            <p className="text-gray-300">{bet.event_description}</p>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-white/5 rounded">
                <Users className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                <p className="text-gray-400 text-sm">Criado por</p>
                <p className="text-white font-semibold">{bet.creator_name}</p>
              </div>
              
              <div className="text-center p-3 bg-white/5 rounded">
                <DollarSign className="w-6 h-6 text-green-400 mx-auto mb-2" />
                <p className="text-gray-400 text-sm">Valor da Aposta</p>
                <p className="text-white font-semibold text-lg">{formatCurrency(bet.amount)}</p>
              </div>
            </div>

            <Badge variant="outline" className="border-white/20 text-white">
              {bet.event_type}
            </Badge>
          </div>

          {/* Time Remaining */}
          <div className="bg-orange-500/20 rounded-lg p-3 border border-orange-500/30 text-center">
            <p className="text-orange-200">
              ⏰ <strong>Tempo restante para aceitar:</strong> {formatTimeRemaining(bet.expires_at)}
            </p>
          </div>

          {/* Prize Information */}
          <div className="bg-green-500/20 rounded-lg p-4 border border-green-500/30">
            <h4 className="text-white font-semibold mb-2">💰 Informações do Prêmio</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-300">Valor total do pote:</span>
                <span className="text-white font-semibold">{formatCurrency(bet.amount * 2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Taxa da plataforma (20%):</span>
                <span className="text-yellow-400">-{formatCurrency(bet.amount * 2 * 0.20)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Prêmio para o vencedor:</span>
                <span className="text-green-400 font-semibold">{formatCurrency(bet.amount * 2 * 0.80)}</span>
              </div>
            </div>
          </div>

          {/* Protection Info */}
          <div className="bg-blue-500/20 rounded-lg p-4 border border-blue-500/30">
            <h4 className="text-white font-semibold mb-2">🛡️ Proteção Garantida</h4>
            <p className="text-blue-200 text-sm">
              Seu dinheiro fica protegido na plataforma até a decisão final do juiz. 
              O vencedor recebe automaticamente o prêmio após o resultado.
            </p>
          </div>

          {/* Action Buttons */}
          {currentUser ? (
            <div className="space-y-3">
              {currentUser.balance >= bet.amount ? (
                <Button 
                  onClick={joinBet}
                  disabled={joining}
                  className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-lg py-3"
                >
                  {joining ? 'Entrando na Aposta...' : `Aceitar Convite - Depositar ${formatCurrency(bet.amount)}`}
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
                    Você precisa de {formatCurrency(bet.amount)} para aceitar este convite
                  </p>
                </div>
              )}
              
              <Button 
                onClick={() => navigate('/')}
                variant="outline"
                className="w-full border-white/20 text-white hover:bg-white/10"
              >
                Voltar ao App
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              <Button 
                onClick={() => navigate('/')}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-lg py-3"
              >
                Fazer Login para Aceitar Convite
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default InvitePage;