export interface User {
  id: number;
  email: string;
  name: string;
  created_at: string;
}

export interface ConversationMessage {
  id: number;
  workflow_id: string;
  speaker: 'user' | 'response';
  message: string;
  message_order: number;
  created_at: string;
  user_id: number;
}

export interface ConversationSummary {
  id: number;
  workflow_id: string;
  summary: string;
  created_at: string;
  updated_at: string;
  user_id: number;
}

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

export interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (email: string, password: string, name: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}