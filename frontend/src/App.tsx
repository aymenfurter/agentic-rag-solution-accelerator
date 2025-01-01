import React, { useState, useEffect } from 'react';
import { Stack, IStackTokens } from '@fluentui/react';
import { Chat } from './components/Chat';
import { FileUpload } from './components/FileUpload';
import { SetupWizard } from './components/SetupWizard';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { isAuthenticated } from './utils/auth';

const stackTokens: IStackTokens = { childrenGap: 20 };

const App: React.FC = () => {
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    // Check if app is already configured
    // This could check local storage or make an API call
  }, []);

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
      <Header />
      <Stack tokens={stackTokens} className="main-content">
        <FileUpload />
        <Chat />
      </Stack>
      <Footer />
    </div>
  );
};

export default App;