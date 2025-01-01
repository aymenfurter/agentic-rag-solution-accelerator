import React from 'react';
import ReactDOM from 'react-dom/client';
import { initializeIcons } from '@fluentui/react';
import App from './App';
import './styles/index.css';

initializeIcons();

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);