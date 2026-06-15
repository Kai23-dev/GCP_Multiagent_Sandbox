// Google OAuth type definitions
export interface GoogleOAuth {
  accounts: {
    oauth2: {
      initTokenClient: (config: TokenClientConfig) => TokenClient;
      initCodeClient: (config: CodeClientConfig) => CodeClient;
      hasGrantedAllScopes: (tokenResponse: TokenResponse, ...scopes: string[]) => boolean;
      hasGrantedAnyScope: (tokenResponse: TokenResponse, ...scopes: string[]) => boolean;
      revoke: (accessToken: string, callback?: () => void) => void;
    };
  };
}

export interface TokenClientConfig {
  client_id: string;
  scope: string;
  callback?: (response: TokenResponse) => void;
  error_callback?: (error: ErrorResponse) => void;
  hint?: string;
  hosted_domain?: string;
  prompt?: string;
}

export interface CodeClientConfig {
  client_id: string;
  scope: string;
  callback?: (response: CodeResponse) => void;
  error_callback?: (error: ErrorResponse) => void;
  redirect_uri?: string;
  ux_mode?: 'popup' | 'redirect';
}

export interface TokenClient {
  requestAccessToken: (overrideConfig?: Partial<TokenClientConfig>) => void;
}

export interface CodeClient {
  requestCode: () => void;
}

export interface TokenResponse {
  access_token: string;
  expires_in: number;
  scope: string;
  token_type: string;
  error?: string;
  error_description?: string;
  error_uri?: string;
}

export interface CodeResponse {
  code: string;
  scope: string;
  authuser: string;
  prompt: string;
}

export interface ErrorResponse {
  type: string;
  message: string;
}

declare global {
  interface Window {
    google?: GoogleOAuth;
  }
}