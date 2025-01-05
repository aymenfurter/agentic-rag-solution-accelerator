import React, { useState } from 'react';
import { 
  Stack, 
  TextField, 
  DefaultButton,
  PrimaryButton,
  MessageBar, 
  MessageBarType,
  Text,
  Label,
  IconButton,
  Dropdown,
  IDropdownOption,
  Toggle,
} from '@fluentui/react';
import MonacoEditor from '@monaco-editor/react';
import { Template } from '../types';

interface TemplateEditorProps {
  template: Template;
  onUpdate: (template: Template) => void;
  onCancel: () => void;
}

const BEST_PRACTICES = `Best Practices for Field Descriptions:
- Include allowed values in the description (e.g., "Valid values: high, medium, low")
- Be specific about format expectations (e.g., "Date format: YYYY-MM-DD")
- Provide examples in the description
- Keep descriptions concise but informative
- Only "generate" method is currently supported
`;

const validateTemplate = (template: any): string[] => {
  const errors: string[] = [];
  
  if (!template.name) errors.push("Template name is required");
  if (!template.fields?.length) errors.push("At least one field is required");
  
  template.fields?.forEach((field: any, index: number) => {
    if (!field.name) errors.push(`Field ${index + 1}: Name is required`);
    if (!field.type) errors.push(`Field ${index + 1}: Type is required`);
    if (!field.description) errors.push(`Field ${index + 1}: Description is required`);
    if (field.method && field.method !== "generate") {
      errors.push(`Field ${index + 1}: Only "generate" method is supported`);
    }
  });

  return errors;
};

const fieldTypes: IDropdownOption[] = [
  { key: 'string', text: 'String' },
  { key: 'number', text: 'Number' },
  { key: 'boolean', text: 'Boolean' },
  { key: 'array', text: 'Array' },
  { key: 'object', text: 'Object' }
];

export const TemplateEditor: React.FC<TemplateEditorProps> = ({ 
  template, 
  onUpdate, 
  onCancel 
}) => {
  const [editedTemplate, setEditedTemplate] = useState(template);
  const [error, setError] = useState<string | null>(null);
  const [isJsonMode, setIsJsonMode] = useState(false);
  const [jsonContent, setJsonContent] = useState(JSON.stringify(template, null, 2));

  const scenarioOptions = [
    { key: 'document', text: 'Document' },
    { key: 'conversation', text: 'Conversation' }
  ];

  const handleJsonChange = (value: string | undefined) => {
    setJsonContent(value || '');
    try {
      const parsed = JSON.parse(value || '');
      const validationErrors = validateTemplate(parsed);
      if (validationErrors.length === 0) {
        setEditedTemplate(parsed);
        setError(null);
      } else {
        setError(validationErrors.join('\n'));
      }
    } catch (e) {
      setError('Invalid JSON format');
    }
  };

  const handleFieldChange = (index: number, field: string, value: any) => {
    const updatedFields = [...editedTemplate.fields];
    updatedFields[index] = {
      ...updatedFields[index],
      [field]: value
    };
    setEditedTemplate({
      ...editedTemplate,
      fields: updatedFields
    });
  };

  const addField = () => {
    setEditedTemplate({
      ...editedTemplate,
      fields: [
        ...editedTemplate.fields,
        { name: '', type: 'string', description: '', method: 'generate' }
      ]
    });
  };

  const removeField = (index: number) => {
    const updatedFields = editedTemplate.fields.filter((_, i) => i !== index);
    setEditedTemplate({
      ...editedTemplate,
      fields: updatedFields
    });
  };

  return (
    <Stack tokens={{ childrenGap: 24 }} className="template-editor-container">
      <Stack 
        horizontal 
        horizontalAlign="space-between" 
        verticalAlign="center"
        className="template-editor-header"
      >
        <Toggle 
          label="🛠️ Pro Mode (JSON)"
          checked={isJsonMode}
          onChange={(_, checked) => setIsJsonMode(checked)}
        />
      </Stack>

      {error && (
        <MessageBar messageBarType={MessageBarType.error}>
          ⚠️ {error}
        </MessageBar>
      )}

      {isJsonMode ? (
        <Stack.Item style={{ height: '600px' }}>
          <MonacoEditor
            language="json"
            theme="vs-light"
            value={jsonContent}
            onChange={handleJsonChange}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              wordWrap: 'on',
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        </Stack.Item>
      ) : (
        <>
          <TextField
            label="Template Name"
            value={editedTemplate.name}
            styles={{
              root: { marginBottom: 16 },
              field: { fontSize: '16px', padding: '8px 12px' }
            }}
            onChange={(_, newValue) => 
              setEditedTemplate({...editedTemplate, name: newValue || ''})
            }
          />

          <TextField
            label="Description"
            multiline
            rows={3}
            value={editedTemplate.description}
            styles={{
              root: { marginBottom: 24 },
              field: { fontSize: '16px', padding: '8px 12px' }
            }}
            onChange={(_, newValue) => 
              setEditedTemplate({...editedTemplate, description: newValue || ''})
            }
          />

          <Dropdown
            label="Scenario"
            selectedKey={editedTemplate.scenario || 'document'}
            options={scenarioOptions}
            onChange={(_, option) => {
              if (option) {
                setEditedTemplate({
                  ...editedTemplate,
                  scenario: option.key as string
                });
              }
            }}
          />

          <Stack>
            {editedTemplate.fields.map((field, index) => (
              <Stack key={index} className="field-row">
                <div className="field-controls">
                  <button
                    className="delete-button"
                    onClick={() => removeField(index)}
                    title="Delete field"
                  >
                    🗑️ 
                  </button>
                </div>
                <div className="field-input-group">
                  <TextField
                    label="Name"
                    value={field.name}
                    onChange={(_, value) => handleFieldChange(index, 'name', value)}
                  />
                  <Dropdown
                    label="Type"
                    selectedKey={field.type}
                    options={fieldTypes}
                    onChange={(_, option) => handleFieldChange(index, 'type', option?.key)}
                  />
                  <TextField
                    label="Description"
                    value={field.description}
                    onChange={(_, value) => handleFieldChange(index, 'description', value)}
                  />
                </div>
              </Stack>
            ))}
            <DefaultButton
              className="add-field-button"
              onClick={addField}
            >
              ➕ Add New Field
            </DefaultButton>
          </Stack>

          <TextField
            label="Instructions"
            multiline
            rows={5}
            value={editedTemplate.instructions}
            styles={{
              root: { marginTop: 24 },
              field: { fontSize: '16px', padding: '8px 12px' }
            }}
            onChange={(_, newValue) => 
              setEditedTemplate({...editedTemplate, instructions: newValue || ''})
            }
          />
        </>
      )}

      <Stack 
        horizontal 
        tokens={{ childrenGap: 12 }} 
        horizontalAlign="end"
        styles={{ root: { marginTop: 32, borderTop: '1px solid #e5e5e5', paddingTop: 24 } }}
      >
        <PrimaryButton 
          text="Save Changes" 
          onClick={() => onUpdate(isJsonMode ? JSON.parse(jsonContent) : editedTemplate)} 
          disabled={!!error}
        />
        <DefaultButton text="Cancel" onClick={onCancel} />
      </Stack>
    </Stack>
  );
};
