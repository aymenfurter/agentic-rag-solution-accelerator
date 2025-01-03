// /src/components/Chat.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Stack, TextField, PrimaryButton, Text } from '@fluentui/react';
import { ChatMessage } from '../types';
import { sendChatMessage, loadChatHistory, createChatThread } from '../utils/api';
import { v4 as uuidv4 } from 'uuid';

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [threadId, setThreadId] = useState<string>('');
  const chatEndRef = useRef<null | HTMLDivElement>(null);

  useEffect(() => {
    const initializeChat = async () => {
      // Get thread ID from local storage or create new one
      const savedThreadId = localStorage.getItem('chatThreadId');
      
      if (savedThreadId) {
        setThreadId(savedThreadId);
        try {
          const history = await loadChatHistory(savedThreadId);
          setMessages(history.messages);
        } catch (error) {
          console.error('Error loading chat history:', error);
          // If loading fails, create new thread
          await createNewThread();
        }
      } else {
        await createNewThread();
      }
    };

    const createNewThread = async () => {
      try {
        const { threadId: newThreadId } = await createChatThread();
        localStorage.setItem('chatThreadId', newThreadId);
        setThreadId(newThreadId);
        setMessages([]);
      } catch (error) {
        console.error('Error creating chat thread:', error);
      }
    };

    initializeChat();
  }, []);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async () => {
    if (!input.trim() || !threadId) return;

    setLoading(true);
    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    try {
      const response = await sendChatMessage(input, threadId);
      const assistantMessage: ChatMessage = {
        role: response.role,
        content: response.content,
        timestamp: response.timestamp
      };

      setMessages([...messages, userMessage, assistantMessage]);
    } catch (error) {
      console.error('Error in chat:', error);
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date().toISOString()
      };
      setMessages([...messages, userMessage, errorMessage]);
    }

    setLoading(false);
    setInput('');
  };

  return (
    <Stack tokens={{ childrenGap: 10 }} className="chat-container">
      <h2>Chat Interface</h2>
      {messages.map((message, index) => (
        <div
          key={index}
          className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
        >
          <Text variant="mediumPlus">{message.content}</Text>
          {message.role === 'assistant' && message.audioUrl && (
            <AudioPlayer audioUrl={message.audioUrl} jumpTime={message.jumpTime} />
          )}
        </div>
      ))}
      <div ref={chatEndRef} />
      
      <Stack horizontal tokens={{ childrenGap: 10 }}>
        <TextField
          multiline
          rows={2}
          value={input}
          onChange={(_, newValue) => setInput(newValue || '')}
          placeholder="Type your message..."
          disabled={loading}
        />
        <PrimaryButton 
          text="Send"
          onClick={handleSubmit}
          disabled={loading || !input.trim()}
        />
      </Stack>
    </Stack>
  );
};