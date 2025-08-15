'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { ConversationMessage, ConversationSummary } from '@/types';

interface ConversationWithSummary {
  workflow_id: string;
  summary: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface ConversationDetail {
  workflow_id: string;
  messages: ConversationMessage[];
  summary: ConversationSummary | null;
}

export default function HistoryViewer() {
  const [conversations, setConversations] = useState<ConversationWithSummary[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const response = await fetch('/api/chat/history');
      if (response.ok) {
        const data = await response.json();
        setConversations(data.conversations);
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadConversationDetail = async (workflowId: string) => {
    setDetailLoading(true);
    try {
      const response = await fetch(`/api/chat/history?workflowId=${encodeURIComponent(workflowId)}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedConversation(data.conversation);
      }
    } catch (error) {
      console.error('Error loading conversation detail:', error);
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading conversations...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-white shadow-sm border-b px-4 py-3">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-800">Conversation History</h1>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">Welcome, {user?.name}</span>
            <button
              onClick={() => window.close()}
              className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 rounded-md"
            >
              Close
            </button>
          </div>
        </div>
      </div>

      <div className="flex h-screen">
        {/* Conversations List */}
        <div className="w-1/3 bg-white border-r overflow-y-auto">
          <div className="p-4">
            <h2 className="text-lg font-medium mb-4">Your Conversations</h2>
            {conversations.length === 0 ? (
              <p className="text-gray-500">No conversations found.</p>
            ) : (
              <div className="space-y-2">
                {conversations.map((conv) => (
                  <div
                    key={conv.workflow_id}
                    onClick={() => loadConversationDetail(conv.workflow_id)}
                    className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                      selectedConversation?.workflow_id === conv.workflow_id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200'
                    }`}
                  >
                    <div className="font-medium text-sm text-gray-800 mb-1">
                      {conv.workflow_id}
                    </div>
                    <div className="text-xs text-gray-600 mb-2">
                      {conv.message_count} messages • {new Date(conv.updated_at).toLocaleDateString()}
                    </div>
                    {conv.summary && (
                      <div className="text-xs text-gray-500 line-clamp-2">
                        {conv.summary}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Conversation Detail */}
        <div className="flex-1 bg-gray-50">
          {selectedConversation ? (
            <div className="h-full flex flex-col">
              <div className="bg-white border-b px-4 py-3">
                <h3 className="font-medium">{selectedConversation.workflow_id}</h3>
                {selectedConversation.summary && (
                  <p className="text-sm text-gray-600 mt-1">
                    {selectedConversation.summary.summary}
                  </p>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                {detailLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-lg">Loading conversation...</div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {selectedConversation.messages.map((message, index) => (
                      <div
                        key={index}
                        className={`flex ${
                          message.speaker === 'user' ? 'justify-end' : 'justify-start'
                        }`}
                      >
                        <div
                          className={`message-bubble ${
                            message.speaker === 'user' ? 'user-message' : 'bot-message'
                          }`}
                        >
                          <p className="text-sm">{message.message}</p>
                          <span className="text-xs opacity-70 mt-1 block">
                            {new Date(message.created_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                <p className="text-lg mb-2">Select a conversation to view details</p>
                <p className="text-sm">Choose from your conversation history on the left</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}