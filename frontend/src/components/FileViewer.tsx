import React, { useEffect, useState } from 'react';
import { Dialog, DialogType, Icon, IconButton } from '@fluentui/react';
import { getFile } from '../utils/api';
import { Button } from '@fluentui/react-components';

interface FileViewerProps {
  filename: string;
  isOpen: boolean;
  onDismiss: () => void;
}

export const FileViewer: React.FC<FileViewerProps> = ({ filename, isOpen, onDismiss }) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [fileType, setFileType] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadFile();
    }
    return () => {
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [isOpen, filename]);

  const loadFile = async () => {
    setLoading(true);
    setError(null);
    try {
      const blob = await getFile(filename);
      const url = URL.createObjectURL(blob);
      setFileUrl(url);
      setFileType(blob.type);
    } catch (error) {
      console.error('Error loading file:', error);
      setError('Failed to load file. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getFileIcon = () => {
    if (fileType?.startsWith('video/')) return '📹';
    if (fileType?.startsWith('audio/')) return '🎵';
    if (fileType === 'application/pdf') return '📄';
    if (fileType?.startsWith('image/')) return '🖼️';
    return '📎';
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="file-viewer-loading">
          <div className="file-viewer-loading-spinner" />
          <span>Loading file...</span>
        </div>
      );
    }

    if (error) {
      return (
        <div className="file-viewer-error">
          <Icon iconName="ErrorBadge" className="error-icon" />
          <p>{error}</p>
          <button className="file-viewer-download" onClick={loadFile}>
            Try Again
          </button>
        </div>
      );
    }

    if (!fileUrl) return null;

    if (fileType?.startsWith('video/')) {
      return (
        <video className="file-viewer-video" controls>
          <source src={fileUrl} type={fileType} />
          Your browser does not support the video tag.
        </video>
      );
    }

    if (fileType?.startsWith('audio/')) {
      return (
        <div className="file-viewer-audio">
          <audio controls controlsList="nodownload noplaybackrate">
            <source src={fileUrl} type={fileType} />
            Your browser does not support the audio tag.
          </audio>
        </div>
      );
    }

    if (fileType === 'application/pdf') {
      return (
        <iframe
          className="file-viewer-pdf"
          src={fileUrl}
          title="PDF Viewer"
        />
      );
    }

    if (fileType?.startsWith('image/')) {
      return <img className="file-viewer-media" src={fileUrl} alt="Preview" />;
    }

    return (
      <div className="file-viewer-error">
        <p>This file type cannot be previewed in the browser.</p>
        <button 
          className="file-viewer-download"
          onClick={() => window.open(fileUrl)}
        >
          <Icon iconName="Download" />
          Download File
        </button>
      </div>
    );
  };

  return (
    <Dialog
      hidden={!isOpen}
      onDismiss={onDismiss}
      dialogContentProps={{
        type: DialogType.normal,
        title: filename,
        className: 'file-viewer-dialog',
        styles: {
          inner: { padding: 0 },
          innerContent: { padding: 0 }
        }
      }}
      modalProps={{
        isBlocking: false,
        styles: { 
          main: { 
            maxWidth: '80vw', 
            minWidth: '40vw',
            overflow: 'hidden'
          },
          scrollableContent: {
            overflow: 'hidden'
          }
        }
      }}
    >
      <div className="file-viewer-header">
        <div className="file-viewer-title">
          {getFileIcon()}
          <span>{filename}</span>
        </div>
        <button class="small-button" onClick={onDismiss}>Close</button>
      </div>
      <div className="file-viewer-content">
        {renderContent()}
      </div>
    </Dialog>
  );
};
