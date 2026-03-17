import { useHandleSignInCallback } from '@logto/react';
import { useNavigate } from 'react-router-dom';

export default function Callback() {
  const navigate = useNavigate();
  const { isLoading } = useHandleSignInCallback(() => navigate('/'));
  return isLoading ? (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#11111b', color: '#cdd6f4' }}>
      <p>登录中...</p>
    </div>
  ) : null;
}
