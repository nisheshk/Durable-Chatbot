'use client';

import { AuthProvider, useAuth } from '@/components/AuthContext';
import LoginForm from '@/components/LoginForm';
import ChatInterface from '@/components/ChatInterface';

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return user ? <ChatInterface /> : <LoginForm />;
}

export default function Home() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}