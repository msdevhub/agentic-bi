import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { LogtoProvider, LogtoConfig } from '@logto/react'
import App from './App'
import Callback from './components/Callback'
import ProtectedRoute from './components/ProtectedRoute'

const logtoConfig: LogtoConfig = {
  endpoint: 'https://logto.dr.restry.cn',
  appId: 'a749dyaep3vsnv6pdu0jx',
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <LogtoProvider config={logtoConfig}>
      <BrowserRouter>
        <Routes>
          <Route path="/callback" element={<Callback />} />
          <Route
            path="*"
            element={
              <ProtectedRoute>
                <App />
              </ProtectedRoute>
            }
          />
        </Routes>
      </BrowserRouter>
    </LogtoProvider>
  </React.StrictMode>,
)
