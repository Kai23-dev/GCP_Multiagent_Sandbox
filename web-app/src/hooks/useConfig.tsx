'use client';

import { useState, useEffect } from 'react';

interface GCPConfig {
  projectId: string;
  location: string;
}

interface EnvironmentConfig {
  nodeEnv: string;
  isCloudRun: boolean;
  iapEnabled: boolean;
}

interface Config {
  gcp: GCPConfig;
  environment: EnvironmentConfig;
}

/**
 * Hook to fetch runtime configuration from the API
 * This solves the issue of NEXT_PUBLIC_ variables not being available at runtime in Cloud Run
 */
export function useConfig() {
  const [config, setConfig] = useState<Config | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/config')
      .then(res => res.json())
      .then(data => {
        setConfig(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to fetch config:', err);
        setError(err.message);
        setLoading(false);

        // Fallback to environment variables if available (for local development)
        setConfig({
          gcp: {
            projectId: process.env.GOOGLE_CLOUD_PROJECT || '',
            location: process.env.GOOGLE_CLOUD_LOCATION || 'us-central1',
          },
          environment: {
            nodeEnv: process.env.NODE_ENV || 'development',
            isCloudRun: false,
            iapEnabled: false,
          }
        });
      });
  }, []);

  return { config, loading, error };
}