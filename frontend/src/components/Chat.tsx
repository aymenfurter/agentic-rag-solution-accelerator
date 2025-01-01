// /src/components/Chat.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Stack, TextField, PrimaryButton, Text } from '@fluentui/react';
import { ChatMessage, SearchResult } from '../types';
import { searchArtifacts, searchChunks } from '../utils/api';
import AudioPlayer from './AudioPlayer';

export const Chat: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async () => {
    if (!input.trim()) return;

    setLoading(true);
    const userMessage: ChatMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    try {
      // First try artifact-level search
      const artifactResults = await searchArtifacts({
        searchText: input,
        semanticRanking: true,
        topK: 3
      });

      // If no high-level results, try chunk-level search
      if (!artifactResults.results.length) {
        const chunkResults = await searchChunks({
          searchText: input,
          semanticRanking: true,
          questionRewriting: true,
          topK: 5
        });

        // Process results and add to chat
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: processResults(chunkResults.results),
          timestamp: new Date().toISOString()
        };

        setMessages([...messages, userMessage, assistantMessage]);
      } else {
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: processResults(artifactResults.results),
          timestamp: new Date().toISOString()
        };

        setMessages([...messages, userMessage, assistantMessage]);
      }
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

  const processResults = (results: SearchResult[]) => {
    // Process and format the search results
    // This could be enhanced with better result formatting
    return results.map(result => result.content).join('\n\n');
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