import React, { useState, useRef } from 'react';
import { Panel, Stack, ProgressIndicator, MessageBar, MessageBarType, PrimaryButton } from '@fluentui/react';
import { uploadFile } from '../utils/api';

interface SettingsMenuProps {
  onReset: () => void;
}

export const SettingsMenu: React.FC<SettingsMenuProps> = ({ onReset }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ type: MessageBarType; message: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadStatus(null);

    try {
      console.log('Uploading file:', file.name);
      const metadata = {
        timestamp: new Date().toISOString(),
        originalName: file.name
      };

      await uploadFile(file, metadata);
      
      setUploadStatus({
        type: MessageBarType.success,
        message: `Successfully uploaded ${file.name}`
      });
      
      setTimeout(() => setShowUpload(false), 1500);
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus({
        type: MessageBarType.error,
        message: 'Failed to upload file. Please try again.'
      });
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <>
      <button onClick={() => setIsOpen(true)} className="settings-button">⚙️</button>
      
      <Panel
        isOpen={isOpen}
        onDismiss={() => setIsOpen(false)}
        isLightDismiss
      >
        <Stack tokens={{ padding: 20, childrenGap: 12 }}>
          <button
            className="settings-menu-button"
            onClick={() => setShowUpload(true)}
          >
            <span>📄</span>
            <span>Upload File</span>
          </button>
        </Stack>
      </Panel>
      
      <Panel
        isOpen={showUpload}
        onDismiss={() => setShowUpload(false)}
        isLightDismiss
        headerText="Upload File"
      >
        <div style={{ padding: 20 }}>
          <Stack tokens={{ childrenGap: 15 }}>
            <input
              type="file"
              onChange={handleFileChange}
              ref={fileInputRef}
              style={{ display: 'none' }}
            />
            <PrimaryButton 
              text="Select File to Upload"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            />
            <p style={{ margin: 0, fontSize: '14px', color: '#666' }}>
              It may take a few minutes for newly processed files to appear in the chat.
            </p>
          </Stack>

          {uploading && (
            <ProgressIndicator 
              label="Uploading..."
              styles={{ root: { marginTop: 20 } }}
            />
          )}

          {uploadStatus && (
            <MessageBar
              messageBarType={uploadStatus.type}
              styles={{ root: { marginTop: 20 } }}
            >
              {uploadStatus.message}
            </MessageBar>
          )}
        </div>
      </Panel>
    </>
  );
};
