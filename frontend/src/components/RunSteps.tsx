import React, { useState } from 'react';
import { Text } from '@fluentui/react';
import { Step } from '../types';
import { FileViewer } from './FileViewer';

const extractStepData = (stepDetails: string) => {
  try {
    const result: { searchQuery?: string; fileNames?: string[]; filter?: string } = {};
    
    const searchMatch = stepDetails.match(/searchText\":\"([^\"]+)\"/);
    if (searchMatch && searchMatch[1]) {
      result.searchQuery = searchMatch[1];
    }

    const filterMatch = stepDetails.match(/filter\":\"([^\"]+)\"/);
    if (filterMatch && filterMatch[1]) {
      result.filter = filterMatch[1];
    }

    const fileNames: string[] = [];
    const fileNameRegex = /\"fileName\":\s*\"([^\"]+)\"/g;
    let match;
    while ((match = fileNameRegex.exec(stepDetails)) !== null) {
      fileNames.push(match[1]);
    }
    if (fileNames.length > 0) {
      result.fileNames = fileNames;
    }

    return result;
  } catch (e) {
    console.error('Parse error:', e);
    return null;
  }
};

export const RunSteps: React.FC<{ steps: Step[] }> = ({ steps }) => {
  const [expanded, setExpanded] = useState(false);
  const [showDetails, setShowDetails] = useState<Record<string, boolean>>({});
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const toggleDetails = (stepId: string) => {
    setShowDetails(prev => ({
      ...prev,
      [stepId]: !prev[stepId]
    }));
  };

  return (
    <div>
      {steps.length >= 2 && (
        <div className="run-steps-container">
          <div className="run-steps-header" onClick={() => setExpanded(!expanded)}>
            <div className="run-steps-summary">
              <Text variant="mediumPlus">🔄 Agent Steps ({steps.length})</Text>
              <Text variant="small">
                Click to {expanded ? 'collapse' : 'expand'} details
              </Text>
            </div>
            <span className="expand-icon">{expanded ? '▼' : '▶'}</span>
          </div>
        
          {expanded && (
            <div className="run-steps-details">
              {steps.map((step, i) => {
                const stepId = step._data.id;
                const stepData = extractStepData(step._data.step_details);
                const showDetailsForStep = showDetails[stepId];

                return (
                  <div key={i} className="step-item">
                    <div className="step-header">
                      <div className="step-info">
                        <Text variant="medium">
                          <b>Step {i + 1}:</b> {step._data.step_details.includes('tool_calls') ? 'Tool Call' : 'Message Creation'}
                        </Text>
                        {stepData && (stepData.searchQuery || stepData.filter || (stepData.fileNames && stepData.fileNames.length > 0)) && (
                          <div className="step-extracted-fields">
                            {stepData.searchQuery && (
                              <div className="step-field">
                                <span className="field-label">Search:</span>
                                <span className="field-value">{stepData.searchQuery}</span>
                              </div>
                            )}
                            {stepData.filter && (
                              <div className="step-field">
                                <span className="field-label">Filter:</span>
                                <span className="field-value">{stepData.filter}</span>
                              </div>
                            )}
                            {stepData.fileNames && stepData.fileNames.length > 0 && (
                              <div className="step-field">
                                <span className="field-label">Files:</span>
                                <span className="field-value">
                                  {stepData.fileNames.map((fileName, index) => (
                                    <React.Fragment key={`${fileName}-${index}-${stepId}`}>
                                      {index > 0 && ', '}
                                      <a
                                        href="#"
                                        onClick={(e) => {
                                          e.preventDefault();
                                          setSelectedFile(fileName);
                                        }}
                                        className="file-link"
                                      >
                                        {fileName}
                                      </a>
                                    </React.Fragment>
                                  ))}
                                </span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      
                      <div className="step-actions">
                        <button 
                          className="small-button"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleDetails(stepId);
                          }}
                        >
                          {showDetailsForStep ? 'Hide JSON' : 'Show JSON'}
                        </button>
                      </div>
                    </div>
                    
                    {showDetailsForStep && (
                      <pre className="step-raw-json">
                        {JSON.stringify(step._data.step_details, null, 2)}
                      </pre>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
      <FileViewer
        filename={selectedFile || ''}
        isOpen={!!selectedFile}
        onDismiss={() => setSelectedFile(null)}
      />
    </div>
  );
};
