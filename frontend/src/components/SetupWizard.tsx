import React, { useState, useEffect } from 'react';
import { 
  Stack, 
  PrimaryButton, 
  Text,
  Spinner,
  MessageBar,
  MessageBarType,
  Image,
  IconButton,
  DefaultButton  // Add this import
} from '@fluentui/react';
import { Template } from '../types';
import { setupAgent, checkSetupStatus } from '../utils/api';
import { TemplateEditor } from './TemplateEditor';

interface SetupWizardProps {
  onComplete: (template: Template) => void;
}

const TEMPLATE_ICONS: Record<string, string> = {
  'email-summarizer': '📧',
  'legal-analysis': '⚖️',
  'medical-case': '🏥',
  'product-review': '🛍️',
  'insurance-claim': '📄',
  'video-analyzer': '🎥',
  'call-center': '📞',
  'standard-rag': '🤖',
};

export const SetupWizard: React.FC<SetupWizardProps> = ({ onComplete }) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [customizedTemplates, setCustomizedTemplates] = useState<Set<string>>(new Set());

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const status = await checkSetupStatus();
        if (status.isConfigured) {
          // If already configured, skip setup
          onComplete({} as Template);
          return;
        }

        // Load all templates
        const [
          emailJson,
          legalJson,
          medicalJson,
          productJson,
          insuranceJson,
          videoJson,
          callCenterJson,
          standardRagJson
        ] = await Promise.all([
          import('../templates/email-summarizer.json'),
          import('../templates/legal-document-analysis.json'),
          import('../templates/medical-case-extractor.json'),
          import('../templates/product-review.json'),
          import('../templates/insurance-claim-analyzer.json'),
          import('../templates/video-analyzer.json'),
          import('../templates/callcenter.json'),
          import('../templates/standardrag.json')
        ]);

        const templatesData = [
          { id: 'email-summarizer', ...emailJson },
          { id: 'legal-analysis', ...legalJson },
          { id: 'medical-case', ...medicalJson },
          { id: 'product-review', ...productJson },
          { id: 'insurance-claim', ...insuranceJson },
          { id: 'video-analyzer', ...videoJson },
          { id: 'call-center', ...callCenterJson },
          { id: 'standard-rag', ...standardRagJson }
        ];

        setTemplates(templatesData);
      } catch (error) {
        setError('Failed to check setup status or load templates');
        console.error('Error:', error);
      } finally {
        setIsLoading(false);
      }
    };

    checkStatus();
  }, [onComplete]);

  const handleSubmit = async () => {
    if (!selectedTemplate) return;

    setIsLoading(true);
    try {
      const response = await setupAgent({
        name: selectedTemplate.name,
        fields: selectedTemplate.fields,
        scenario: selectedTemplate.scenario,
        instructions: selectedTemplate.instructions
      });

      if (response.status === 'success') {
        onComplete(selectedTemplate);
      } else {
        setError('Failed to setup agent');
      }
    } catch (error) {
      console.error('Setup error:', error);
      setError('Failed to setup agent');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditTemplate = () => {
    if (!selectedTemplate) return;
    setIsEditing(true);
  };

  const handleTemplateUpdate = (updatedTemplate: Template) => {
    setSelectedTemplate(updatedTemplate);
    setCustomizedTemplates(prev => new Set(prev).add(updatedTemplate.id));
    setIsEditing(false);
  };

  const renderTemplateCard = (template: Template) => {
    const isSelected = selectedTemplate?.id === template.id;
    const isCustomized = customizedTemplates.has(template.id);

    return (
      <Stack 
        className={`template-card ${isSelected ? 'selected' : ''}`}
        onClick={() => setSelectedTemplate(template)}
      >
        <div className="template-header">
          <span className="template-icon">
            {TEMPLATE_ICONS[template.id] || '📋'}
          </span>
          <span className="template-title">{template.name}</span>
        </div>
        
        {isCustomized && (
          <div className="customized-badge">
            Customized
          </div>
        )}

        <Text className="template-description">
          {template.description}
        </Text>

        <Stack 
          horizontal 
          tokens={{ childrenGap: 8 }} 
          styles={{ root: { marginTop: 16 } }}
        >
          {template.fields.slice(0, 3).map((field, idx) => (
            <Text
              key={idx}
              styles={{
                root: {
                  fontSize: '12px',
                  background: '#f3f2f1',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  color: '#605e5c'
                }
              }}
            >
              {field.name}
            </Text>
          ))}
          {template.fields.length > 3 && (
            <Text styles={{ root: { fontSize: '12px', color: '#605e5c' } }}>
              +{template.fields.length - 3} more
            </Text>
          )}
        </Stack>
      </Stack>
    );
  };

  if (isLoading) {
    return (
      <Stack horizontalAlign="center" verticalAlign="center" style={{ height: '80vh' }}>
        <Spinner label="Preparing your experience..." styles={{ label: { marginTop: 8 } }} />
      </Stack>
    );
  }

  if (isEditing && selectedTemplate) {
    return (
      <Stack className="setup-wizard">
        <Stack horizontal horizontalAlign="space-between" verticalAlign="center">
          <Text variant="xLarge" styles={{ root: { fontWeight: 600 } }}>
            Customize Template
          </Text>
          <DefaultButton
            text="Back to Templates"
            onClick={() => setIsEditing(false)}
          />
        </Stack>
        <TemplateEditor
          template={selectedTemplate}
          onUpdate={handleTemplateUpdate}
          onCancel={() => setIsEditing(false)}
        />
      </Stack>
    );
  }

  return (
    <Stack tokens={{ childrenGap: 24 }} className="setup-wizard">
      {error && (
        <MessageBar messageBarType={MessageBarType.error}>
          {error}
        </MessageBar>
      )}
      
      <Stack horizontalAlign="center" tokens={{ childrenGap: 16 }}>
        <Image 
          src="/logo.png" 
          alt="RAG Logo" 
          width={64} 
          height={64} 
        />
        <Text variant="xxLarge" styles={{ root: { fontWeight: 600 } }}>
          Welcome to RAG Solution Accelerator
        </Text>
        <Text variant="large" styles={{ root: { color: '#666', textAlign: 'center', maxWidth: 600 } }}>
          Choose a template to get started with your AI-powered solution
        </Text>
      </Stack>

      <div className="template-grid">
        {templates.map(template => renderTemplateCard(template))}
      </div>

      {selectedTemplate && (
        <Stack 
          horizontal 
          horizontalAlign="center" 
          tokens={{ childrenGap: 12 }}
          styles={{ root: { marginTop: 32 } }}
        >
          <PrimaryButton 
            text="Configure App"
            onClick={handleSubmit}
            disabled={isLoading}
            styles={{
              root: {
                padding: '16px 32px',
                borderRadius: '6px',
                fontSize: '16px'
              }
            }}
          />
          <DefaultButton
            text="Customize Template"
            onClick={handleEditTemplate}
            disabled={isLoading}
            styles={{
              root: {
                padding: '16px 32px',
                borderRadius: '6px',
                fontSize: '16px'
              }
            }}
          />
        </Stack>
      )}
    </Stack>
  );
};