import React from 'react';
import ReactDOM from 'react-dom/client';
import { GoogleOAuthProvider } from '@react-oauth/google';

import App from './App';
import { I18nProvider } from './i18n';

const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

if (!clientId) {
  console.error('Missing VITE_GOOGLE_CLIENT_ID. Check frontend/.env.local.');
}

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Could not find root element to mount to');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={clientId || ''}>
      <I18nProvider>
        <App />
      </I18nProvider>
    </GoogleOAuthProvider>
  </React.StrictMode>
);
