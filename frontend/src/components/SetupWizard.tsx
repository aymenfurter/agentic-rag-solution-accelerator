// /src/components/SetupWizard.tsx
import React, { useState, useEffect } from 'react';
import { 
  Stack, 
  PrimaryButton, 
  Dropdown, 
  TextField, 
  IDropdownOption 
} from '@fluentui/react';
import { Template, Field } from '../types';
import { setupAgent } from '../utils/api';

interface SetupWizardProps {
  onComplete: (template: Template) => void;
}

export const SetupWizard: React.FC<SetupWizardProps> = ({ onComplete }) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [customFields, setCustomFields] = useState<Field[]>([]);

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const callCenterJson = await import('../templates/callcenter.json');
        const standardRagJson = await import('../templates/standardrag.json');

        const callCenterTemplate: Template = {
          id: 'call-center',
          name: callCenterJson.default.name,
          description: callCenterJson.default.description,
          instructions: callCenterJson.default.instructions,
          fields: callCenterJson.default.fields.map(field => ({
            ...field,
            required: false // or true based on your requirements
          }))
        };

        const standardRagTemplate: Template = {
          id: 'standard-rag',
          name: standardRagJson.default.name,
          description: standardRagJson.default.description,
          instructions: standardRagJson.default.instructions,
          fields: standardRagJson.default.fields.map(field => ({
            ...field,
            required: false // or true based on your requirements
          }))
        };

        setTemplates([callCenterTemplate, standardRagTemplate]);
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
      const template = templates.find(t => t.name === option.key);
      if (template) {
        setSelectedTemplate(template.name);
        setCustomFields(template.fields);
      }
    }
  };

  const handleSubmit = async () => {
    try {
      await setupAgent(customFields, selectedTemplate);
      const template = templates.find(t => t.name === selectedTemplate);
      if (template) {
        onComplete(template);
      }
    } catch (error) {
      console.error('Setup error:', error);
    }
  };

  return (
    <Stack tokens={{ childrenGap: 20 }} className="setup-wizard">
      <Dropdown
        label="Select Template"
        options={templates.map(t => ({ key: t.name, text: t.name }))}
        onChange={handleTemplateChange}
      />

      {selectedTemplate && (
        <>
          <Stack tokens={{ childrenGap: 10 }}>
            {customFields.map((field, index) => (
              <TextField
                key={index}
                label={field.name}
                value={field.description}
                onChange={(_, value) => {
                  const newFields = [...customFields];
                  newFields[index].description = value || '';
                  setCustomFields(newFields);
                }}
              />
            ))}
          </Stack>

          <PrimaryButton text="Complete Setup" onClick={handleSubmit} />
        </>
      )}
    </Stack>
  );
};