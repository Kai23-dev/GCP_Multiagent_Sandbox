import { useState, useCallback } from 'react';

interface SessionState {
  sessionId: string | null;
  isClearing: boolean;
}

interface UseAgentSessionReturn {
  sessionId: string | null;
  isClearing: boolean;
  clearSession: () => Promise<void>;
  sendMessage: (message: string, agentId: string, options?: { clearSession?: boolean }) => Promise<{ response: string; sessionId: string; success: boolean }>;
}

export function useAgentSession(): UseAgentSessionReturn {
  const [sessionState, setSessionState] = useState<SessionState>({
    sessionId: null,
    isClearing: false
  });

  const clearSession = useCallback(async () => {
    setSessionState(prev => ({ ...prev, isClearing: true }));
    
    try {
      const response = await fetch('/api/sessions/clear', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to clear session');
      }

      const result = await response.json();
      console.log('Session cleared:', result);
      
      // Reset local session state
      setSessionState({
        sessionId: null,
        isClearing: false
      });

    } catch (error) {
      console.error('Error clearing session:', error);
      setSessionState(prev => ({ ...prev, isClearing: false }));
      throw error;
    }
  }, []);

  const sendMessage = useCallback(async (
    message: string, 
    agentId: string, 
    options: { clearSession?: boolean } = {}
  ) => {
    try {
      const requestBody = {
        message,
        agentId,
        sessionId: sessionState.sessionId,
        clearSession: options.clearSession
      };

      const response = await fetch('/api/agent-engine', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      
      // Update session ID if we got a new one
      if (result.sessionId && result.sessionId !== sessionState.sessionId) {
        setSessionState(prev => ({ 
          ...prev, 
          sessionId: result.sessionId 
        }));
      }

      return result;

    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }, [sessionState.sessionId]);

  return {
    sessionId: sessionState.sessionId,
    isClearing: sessionState.isClearing,
    clearSession,
    sendMessage
  };
}
