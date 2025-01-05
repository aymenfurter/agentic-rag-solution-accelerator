import React, { useState, useRef, useEffect } from 'react';
import { Stack, TextField, Text, List, Spinner, DefaultButton } from '@fluentui/react';
import { ChatMessage, Step, Thread } from '../types';
import { sendChatMessage, createChatThread } from '../utils/api';

const parseMarkdown = (text: string): string => {
  // Headers
  text = text.replace(/^### (.*$)/gm, '<h3>$1</h3>');
  text = text.replace(/^## (.*$)/gm, '<h2>$1</h2>');
  text = text.replace(/^# (.*$)/gm, '<h1>$1</h1>');
  
  // Bold
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Italic
  text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  // Code blocks
  text = text.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  
  // Inline code
  text = text.replace(/`(.*?)`/g, '<code>$1</code>');
  
  // Lists
  text = text.replace(/^\s*[-*]\s(.+)/gm, '<li>$1</li>');
  text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  
  // Line breaks
  text = text.replace(/\n/g, '<br>');
  
  return text;
};

export const Chat: React.FC = () => {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [currentThread, setCurrentThread] = useState<Thread | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const chatEndRef = useRef<null | HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const savedThreads = localStorage.getItem('chatThreads');
    if (savedThreads) {
      setThreads(JSON.parse(savedThreads));
    }
  }, []);

  useEffect(() => {
    inputRef.current?.focus();
  }, [currentThread]);

  const handleNewChat = () => {
    setCurrentThread(null);
    setInput('');
    setTimeout(() => {
      const initialInput = document.querySelector('.initial-input textarea') as HTMLTextAreaElement;
      if (initialInput) {
        initialInput.focus();
      }
    }, 100);
  };

  const deleteThread = (threadId: string) => {
    setThreads(prev => {
      const updated = prev.filter(t => t.id !== threadId);
      localStorage.setItem('chatThreads', JSON.stringify(updated));
      return updated;
    });
    if (currentThread?.id === threadId) {
      setCurrentThread(null);
    }
  };

  const extractStepData = (stepDetails: string) => {
    try {
      // Initialize return object
      const result: { searchQuery?: string; fileNames?: string[]; filter?: string } = {};

      // Extract search text from arguments if present
      const searchMatch = stepDetails.match(/searchText\":\"([^\"]+)\"/);
      if (searchMatch && searchMatch[1]) {
        result.searchQuery = searchMatch[1];
      }

      // Extract filter if present
      const filterMatch = stepDetails.match(/filter\":\"([^\"]+)\"/);
      if (filterMatch && filterMatch[1]) {
        result.filter = filterMatch[1];
      }

      // Extract all filenames
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

  const handleInitialSubmit = async () => {
    if (!input.trim() || loading) return;
    setLoading(true);
    try {
      const { threadId } = await createChatThread();
      const newThread: Thread = {
        id: threadId,
        title: input.slice(0, 30) + '...',
        messages: [],
        createdAt: new Date().toISOString()
      };

      const updatedThreads = [newThread, ...threads];
      localStorage.setItem('chatThreads', JSON.stringify(updatedThreads));
      setThreads(updatedThreads);
      setCurrentThread(newThread);

      const userMessage: ChatMessage = {
        role: 'user',
        content: input,
        timestamp: new Date().toISOString()
      };

      const threadWithUserMessage = { ...newThread, messages: [userMessage] };
      const threadsWithUserMessage = updatedThreads.map(t =>
        t.id === threadId ? threadWithUserMessage : t
      );
      localStorage.setItem('chatThreads', JSON.stringify(threadsWithUserMessage));
      setThreads(threadsWithUserMessage);
      setCurrentThread(threadWithUserMessage);

      setInput('');

      const response = await sendChatMessage(userMessage.content, threadId);

      let parsedSteps: any[] = [];
      if (Array.isArray(response.steps)) {
        parsedSteps = response.steps;
      }

      const assistantMessage: ChatMessage = {
        role: response.role,
        content: response.content,
        timestamp: response.timestamp,
        steps: parsedSteps,
        toolCalls: response.toolCalls
      };

      const finalThread = {
        ...threadWithUserMessage,
        messages: [...threadWithUserMessage.messages, assistantMessage]
      };
      const finalThreads = threadsWithUserMessage.map(t =>
        t.id === threadId ? finalThread : t
      );

      localStorage.setItem('chatThreads', JSON.stringify(finalThreads));
      setThreads(finalThreads);
      setCurrentThread(finalThread);
    } catch (err) {
      console.error('[handleInitialSubmit] error:', err);
    }
    setLoading(false);
  };

  const syncState = (threads: Thread[], currentThreadId: string | null) => {
    try {
      const sanitizedThreads = threads.map(thread => ({
        ...thread,
        messages: thread.messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp,
          steps: msg.steps,
          toolCalls: msg.toolCalls
        }))
      }));
      localStorage.setItem('chatThreads', JSON.stringify(sanitizedThreads));
      const foundThread = threads.find(t => t.id === currentThreadId);
      setThreads(threads);
      setCurrentThread(foundThread || null);
    } catch (e) {
      console.error('[syncState] error:', e);
    }
  };

  const handleSubmit = async (threadId?: string) => {
    if (!input.trim() || loading) return;
    const activeThreadId = threadId || currentThread?.id;
    if (!activeThreadId) return;

    setLoading(true);
    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    const updatedThreads = threads.map(thread => {
      if (thread.id === activeThreadId) {
        return { ...thread, messages: [...thread.messages, userMessage] };
      }
      return thread;
    });
    syncState(updatedThreads, activeThreadId);
    setInput('');

    try {
      const response = await sendChatMessage(input, activeThreadId);

      let parsedSteps: any[] = [];
      if (Array.isArray(response.steps)) {
        parsedSteps = response.steps;
      }

      const assistantMessage: ChatMessage = {
        role: response.role,
        content: response.content,
        timestamp: response.timestamp,
        steps: parsedSteps,
        toolCalls: response.toolCalls
      };

      const threadsWithResponse = updatedThreads.map(thread => {
        if (thread.id === activeThreadId) {
          return { ...thread, messages: [...thread.messages, assistantMessage] };
        }
        return thread;
      });

      syncState(threadsWithResponse, activeThreadId);
    } catch (error) {
      console.error('[handleSubmit] error in chat:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date().toISOString()
      };
      const threadsWithError = updatedThreads.map(thread => {
        if (thread.id === activeThreadId) {
          return { ...thread, messages: [...thread.messages, errorMessage] };
        }
        return thread;
      });
      syncState(threadsWithError, activeThreadId);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (currentThread) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [currentThread]);

  const formatThreadTitle = (thread: Thread) => {
    return new Date(thread.createdAt).toLocaleString();
  };

  const handleKeyPress = (evt: React.KeyboardEvent) => {
    if (evt.key === 'Enter' && !evt.shiftKey) {
      evt.preventDefault();
      if (input.trim() && !loading) {
        if (currentThread) {
          handleSubmit();
        } else {
          handleInitialSubmit();
        }
      }
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      const button = document.activeElement as HTMLButtonElement;
      const originalText = button.innerHTML;
      button.innerHTML = '✓ Copied';
      setTimeout(() => {
        button.innerHTML = originalText;
      }, 1500);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const handleThreadSelect = (thread: Thread) => {
    syncState(threads, thread.id);
    setInput('');
  };

  const RunSteps: React.FC<{ steps: Step[] }> = ({ steps }) => {
    const [expanded, setExpanded] = useState(false);
    const [showDetails, setShowDetails] = useState<Record<string, boolean>>({});

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
                                  <React.Fragment key={fileName}>
                                    {index > 0 && ', '}
                                    <a href="#" onClick={(e) => e.preventDefault()}>
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
      </div>
    );
  };

  const renderMessage = (msg: ChatMessage, index: number) => {
    const hasValidSteps = msg.steps && msg.steps.length > 0;
    return (
      <div key={`${msg.timestamp}-${index}`} className={`message ${msg.role}`}>
        <div className="message-content">
          {msg.role === 'assistant' && hasValidSteps && <RunSteps steps={msg.steps!} />}
          <div 
            className="text-content"
            dangerouslySetInnerHTML={{ __html: parseMarkdown(msg.content) }}
          />
          {msg.role === 'assistant' && msg.content && (
            <button
              className="copy-button"
              onClick={() => copyToClipboard(msg.content)}
              title="Copy to clipboard"
            >
              Copy
            </button>
          )}
        </div>
      </div>
    );
  };

  return (
    <Stack horizontal className="chat-main">
      <Stack horizontal className="chat-controls">
        <button
          className="sidebar-toggle"
          onClick={() => setSidebarVisible(!sidebarVisible)}
          title={sidebarVisible ? 'Hide sidebar' : 'Show sidebar'}
        >
          {sidebarVisible ? '◀' : '▶'}
        </button>
        <DefaultButton className="small-button" text="New Chat" onClick={handleNewChat} />
      </Stack>

      {sidebarVisible && (
        <Stack className="thread-sidebar">
          <List
            items={threads}
            onRenderCell={thread =>
              thread && (
                <Stack
                  className={`thread-item ${
                    thread.id === currentThread?.id ? 'selected' : ''
                  }`}
                  onClick={() => handleThreadSelect(thread)}
                  horizontal
                  verticalAlign="center"
                >
                  <span className="thread-item-content">{formatThreadTitle(thread)}</span>
                  <button
                    className="small-button"
                    onClick={e => {
                      e.stopPropagation();
                      deleteThread(thread.id);
                    }}
                    title="Delete conversation"
                  >
                    Delete
                  </button>
                </Stack>
              )
            }
          />
        </Stack>
      )}

      <Stack className="chat-content">
        {currentThread ? (
          <>
            <div className="messages-container">
              {currentThread.messages.map((m, i) => renderMessage(m, i))}
              {loading && (
                <div className="loading-spinner">
                  <Spinner label="Processing..." />
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <Stack horizontal className="input-container">
              <TextField
                placeholder="Type your message here..."
                value={input}
                onChange={(_, val) => setInput(val || '')}
                multiline
                rows={3}
                disabled={loading}
                onKeyDown={handleKeyPress}
                componentRef={inputRef}
                autoFocus
              />
              <button
                className="send-button"
                onClick={() => handleSubmit()}
                disabled={loading || !input.trim()}
              >
                ➤
              </button>
            </Stack>
          </>
        ) : (
          <Stack className="empty-state">
            <h1>What can I help with?</h1>
            <div className="input-container initial-input">
              <TextField
                placeholder="Message your Agent..."
                multiline
                rows={4}
                value={input}
                onChange={(_, val) => setInput(val || '')}
                onKeyDown={handleKeyPress}
              />
              <button
                className="send-button"
                onClick={handleInitialSubmit}
                disabled={loading || !input.trim()}
              >
                ➤
              </button>
            </div>
          </Stack>
        )}
      </Stack>
    </Stack>
  );
};