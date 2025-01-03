import React, { useState, useEffect } from 'react';
import { 
  Stack, 
  PrimaryButton, 
  Dropdown, 
  Text,
  IDropdownOption 
} from '@fluentui/react';
import { Template } from '../types';
import { setupAgent } from '../utils/api';

interface SetupWizardProps {
  onComplete: (template: Template) => void;
}

export const SetupWizard: React.FC<SetupWizardProps> = ({ onComplete }) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const callCenterJson = await import('../templates/callcenter.json');
        const standardRagJson = await import('../templates/standardrag.json');

        const templatesData = [
          {
            id: 'call-center',
            ...callCenterJson
          },
          {
            id: 'standard-rag',
            ...standardRagJson
          }
        ];

        setTemplates(templatesData);
      } catch (error) {
        console.error('Error loading templates:', error);
      }
    };
    loadTemplates();
  }, []);

  const handleTemplateChange = (
    _event: React.FormEvent<HTMLDivElement>,
    option?: IDropdownOption
  ) => {
    if (option) {
      const template = templates.find(t => t.id === option.key);
      setSelectedTemplate(template || null);
    }
  };

  const handleSkip = () => {
    onComplete({} as Template);

  };
  const handleSubmit = async () => {
    if (!selectedTemplate) return;

    try {
      const response = await setupAgent({
        name: selectedTemplate.name,
        fields: selectedTemplate.fields,
        scenario: selectedTemplate.scenario,
        instructions: selectedTemplate.instructions
      });

      if (response.status === 'success') {
        onComplete(selectedTemplate);
      }
    } catch (error) {
      console.error('Setup error:', error);
    }
  };

  return (
    <Stack tokens={{ childrenGap: 20 }} className="setup-wizard">
      <Dropdown
        label="Select Template"
        options={templates.map(t => ({ 
          key: t.id, 
          text: t.name,
          data: t
        }))}
        onChange={handleTemplateChange}
      />

      {selectedTemplate && (
        <Stack tokens={{ childrenGap: 15 }}>
          <Text variant="large">{selectedTemplate.description}</Text>
          <Text>Scenario: {selectedTemplate.scenario}</Text>
          
          <Stack tokens={{ childrenGap: 10 }}>
            <Text variant="mediumPlus">Fields:</Text>
            {selectedTemplate.fields.map((field, index) => (
              <Stack key={index} tokens={{ childrenGap: 5 }}>
                <Text variant="medium">
                  {field.name} ({field.type})
                </Text>
                <Text variant="small">
                  {field.description}
                </Text>
              </Stack>
            ))}
          </Stack>

          <PrimaryButton 
            text="Complete Setup" 
            onClick={handleSubmit}
          />

<PrimaryButton 
            text="Skip" 
            onClick={handleSkip}
          />
        </Stack>
      )}
    </Stack>
  );
};