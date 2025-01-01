import React, { useCallback, useState } from 'react';
import { Stack, PrimaryButton, Text, ProgressIndicator } from '@fluentui/react';
import { useDropzone } from 'react-dropzone';
import { uploadFile } from '../utils/api';

export const FileUpload: React.FC = () => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setUploading(true);
    setUploadProgress(0);

    try {
      for (const file of acceptedFiles) {
        const metadata = {
          timestamp: new Date().toISOString(),
          originalName: file.name
        };

        await uploadFile(file, metadata);
        setUploadProgress((prev) => prev + (1 / acceptedFiles.length) * 100);
      }
    } catch (error) {
      console.error('Upload error:', error);
    }

    setUploading(false);
    setUploadProgress(0);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    disabled: uploading
  });

  return (
    <Stack tokens={{ childrenGap: 10 }}>
      <h2>File Upload</h2>
      <PrimaryButton text="Upload File" onClick={() => {}} />
      <div {...getRootProps()} className="file-upload">
        <input {...getInputProps()} />
        <Text>
          {isDragActive
            ? "Drop the files here"
            : "Drag 'n' drop files here, or click to select files"}
        </Text>
        {uploading && <ProgressIndicator percentComplete={uploadProgress / 100} />}
      </div>
    </Stack>
  );
};