import { NextResponse } from 'next/server';

/**
 * API endpoint to provide client configuration
 * Simplified for IAP authentication - no OAuth needed on client side
 */
export async function GET() {
  return NextResponse.json({
    gcp: {
      projectId: process.env.GOOGLE_CLOUD_PROJECT,
      location: process.env.GOOGLE_CLOUD_LOCATION || 'us-central1',
    },
    environment: {
      nodeEnv: process.env.NODE_ENV,
      isCloudRun: !!process.env.K_SERVICE,
      iapEnabled: true, // IAP handles authentication
    },
  });
}