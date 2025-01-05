import React, { useState, useEffect } from 'react';
import { Stack } from '@fluentui/react';
import { Chat } from './components/Chat';
import { SetupWizard } from './components/SetupWizard';
import { Header } from './components/Header';
import { SettingsMenu } from './components/SettingsMenu';
import { isAuthenticated } from './utils/auth';

const App: React.FC = () => {
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    // Check if app is already configured
    // This could check local storage or make an API call
  }, []);

  const handleReset = () => {
    localStorage.clear();
    window.location.reload();
  };

  if (!isAuthenticated()) {
    return <div>Please login to continue</div>;
  }

  if (!isConfigured) {
    return (
      <SetupWizard
        onComplete={() => {
          setIsConfigured(true);
        }}
      />
    );
  }

  return (
    <div className="app-container">
      <Stack horizontal className="header" verticalAlign="center">
        <div className="header-left"></div>
        <SettingsMenu onReset={handleReset} />
      </Stack>
      <Chat />
    </div>
  );
};

export default App;