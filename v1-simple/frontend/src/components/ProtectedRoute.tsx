import { useLogto } from '@logto/react';
import React from 'react';

interface Props {
  children: React.ReactNode;
  redirectUri?: string;
}

export default function ProtectedRoute({ children, redirectUri = window.location.origin + '/callback' }: Props) {
  const { isAuthenticated, isLoading, signIn } = useLogto();

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#11111b', color: '#cdd6f4' }}>
        <p>加载中...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#11111b', color: '#cdd6f4', gap: 16 }}>
        <h2 style={{ margin: 0 }}>📊 AIA Agentic BI</h2>
        <p style={{ color: '#6c7086', margin: 0 }}>请登录以继续使用</p>
        <button
          onClick={() => void signIn(redirectUri)}
          style={{ backgroundColor: '#89b4fa', color: '#11111b', border: 'none', borderRadius: 8, padding: '10px 24px', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}
        >
          登录
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
