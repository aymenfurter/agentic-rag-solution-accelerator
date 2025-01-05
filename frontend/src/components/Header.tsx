import React from 'react';
import { Stack, PrimaryButton, Image } from '@fluentui/react';

interface HeaderProps {
  onSkip?: () => void;
  showSkipButton?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onSkip, showSkipButton = true }) => {
  return (
    <Stack 
      horizontal 
      horizontalAlign="space-between" 
      verticalAlign="center" 
      className="header"
    >
      <Stack horizontal verticalAlign="center" tokens={{ childrenGap: 12 }}>
        <Image src="/logo.png" alt="RAG Logo" width={32} height={32} />
        <h1 style={{ margin: 0, fontSize: '1.2rem' }}>RAG Solution Accelerator</h1>
      </Stack>
      {showSkipButton && (
        <PrimaryButton 
          text="Skip to Chat" 
          onClick={onSkip}
          styles={{
            root: {
              borderRadius: '4px',
              padding: '8px 16px'
            }
          }}
        />
      )}
    </Stack>
  );
};