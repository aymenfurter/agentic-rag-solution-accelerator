import React from 'react';
import { Panel, Stack } from '@fluentui/react';
import { FileUpload } from './FileUpload';

interface SettingsMenuProps {
  onReset: () => void;
}

export const SettingsMenu: React.FC<SettingsMenuProps> = ({ onReset }) => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [showUpload, setShowUpload] = React.useState(false);

  return (
    <>
      <button 
        className="settings-button"
        onClick={() => setIsOpen(true)}
        title="Settings"
      >
        ⚙️
      </button>
      
      <Panel
        isOpen={isOpen}
        onDismiss={() => setIsOpen(false)}
        isLightDismiss
        className="settings-panel"
        headerText=""
      >
        <div className="settings-panel-header">
          <h2>Settings</h2>
          <button 
            className="settings-panel-close"
            onClick={() => setIsOpen(false)}
          >
            ✖️
          </button>
        </div>
        <Stack tokens={{ padding: 20, childrenGap: 12 }}>
          <button
            className="settings-menu-button"
            onClick={() => setShowUpload(true)}
          >
            <span>📄</span>
            <span>Upload New Files</span>
          </button>
          <button
            className="settings-menu-button"
            onClick={onReset}
            disabled
          >
            <span>🔄</span>
            <span>Reset App Configuration</span>
          </button>
        </Stack>
      </Panel>
      
      <Panel
        isOpen={showUpload}
        onDismiss={() => setShowUpload(false)}
        isLightDismiss
        className="settings-panel"
        headerText=""
      >
        <div className="settings-panel-header">
          <h2>Upload Files</h2>
          <button 
            className="settings-panel-close"
            onClick={() => setShowUpload(false)}
          >
            ✖️
          </button>
        </div>
        <div style={{ padding: 20 }}>
          <FileUpload />
        </div>
      </Panel>
    </>
  );
};
