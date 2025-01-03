import React from 'react';
import { Stack, PrimaryButton } from '@fluentui/react';

interface HeaderProps {
  onSkip?: () => void;
  showSkipButton?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onSkip, showSkipButton = true }) => {
  return (
    <Stack horizontal horizontalAlign="space-between" className="header">
      <h1>RAG Solution Accelerator</h1>
      {showSkipButton && (
        <PrimaryButton text="Skip to Chat" onClick={onSkip} />
      )}
    </Stack>
  );
};