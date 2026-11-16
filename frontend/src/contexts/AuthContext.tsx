import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (name: string, email: string, pass: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('jurist_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshUser = async () => {
    const currentToken = localStorage.getItem('jurist_token');
    if (!currentToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const userData = await api.getMe();
      setUser(userData);
      localStorage.setItem('jurist_user', JSON.stringify(userData));
    } catch (err) {
      localStorage.removeItem('jurist_token');
      localStorage.removeItem('jurist_user');
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, pass: string) => {
    setIsLoading(true);
    try {
      const data = await api.login({ email, password: pass });
      localStorage.setItem('jurist_token', data.token);
      localStorage.setItem('jurist_user', JSON.stringify(data.user));
      setToken(data.token);
      setUser(data.user);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (name: string, email: string, pass: string) => {
    setIsLoading(true);
    try {
      const data = await api.register({ name, email, password: pass });
      localStorage.setItem('jurist_token', data.token);
      localStorage.setItem('jurist_user', JSON.stringify(data.user));
      setToken(data.token);
      setUser(data.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('jurist_token');
    localStorage.removeItem('jurist_user');
    setToken(null);
    setUser(null);
    api.logout().catch(() => {});
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
