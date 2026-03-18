import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';

// Logto SDK is only loaded in secure contexts (HTTPS).
// In HTTP dev mode, /callback just redirects home.
const isSecure = window.isSecureContext;

function LogtoCallback() {
  // Dynamic import to ensure Logto hooks are only called when provider is present.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { useHandleSignInCallback } = require('@logto/react');
  const navigate = useNavigate();
  const { isLoading } = useHandleSignInCallback(() => navigate('/'));
  return isLoading ? (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#11111b', color: '#cdd6f4' }}>
      <p>登录中...</p>
    </div>
  ) : null;
}

function MockCallback() {
  const navigate = useNavigate();
  useEffect(() => { navigate('/'); }, [navigate]);
  return null;
}

export default function Callback() {
  return isSecure ? <LogtoCallback /> : <MockCallback />;
}
