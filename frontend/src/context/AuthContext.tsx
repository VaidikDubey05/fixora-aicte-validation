import React, { createContext, useContext, useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useMe, UserResponse } from '../api/useMe';
import { Role } from '../lib/vocab';

interface AuthContextType {
  user: UserResponse | null;
  token: string | null;
  role: Role | null;
  isLoading: boolean;
  login: (token: string, user: UserResponse) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = useQueryClient();
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem('fixora_token');
    } catch {
      return null;
    }
  });

  const [storedUser, setStoredUser] = useState<UserResponse | null>(() => {
    try {
      const raw = localStorage.getItem('fixora_user');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  const { data: meUser, isLoading: isMeLoading } = useMe();

  const user = meUser || storedUser;
  const role = (user?.role as Role) || null;

  useEffect(() => {
    if (meUser) {
      setStoredUser(meUser);
      localStorage.setItem('fixora_user', JSON.stringify(meUser));
    }
  }, [meUser]);

  const login = (newToken: string, newUser: UserResponse) => {
    setToken(newToken);
    setStoredUser(newUser);
    localStorage.setItem('fixora_token', newToken);
    localStorage.setItem('fixora_user', JSON.stringify(newUser));
    queryClient.setQueryData(['auth', 'me'], newUser);
  };

  const logout = () => {
    setToken(null);
    setStoredUser(null);
    try {
      localStorage.removeItem('fixora_token');
      localStorage.removeItem('fixora_user');
    } catch {
      // ignore
    }
    // Logout clears the query cache as requested in STEP 3
    queryClient.clear();
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        role,
        isLoading: isMeLoading && !storedUser,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
