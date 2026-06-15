import { NextRequest, NextResponse } from 'next/server';
import { callCloudRunService, getUserFromIAPHeaders } from '@/utils/auth';

// Example of how to use the URL environment variable for service-to-service calls
export async function POST(request: NextRequest) {
  try {
    const { message } = await request.json();
    
    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    // Get the target service URL from environment variable (configured in Terraform)
    const targetServiceUrl = process.env.URL;
    
    if (!targetServiceUrl) {
      return NextResponse.json(
        { error: 'Target service URL not configured' },
        { status: 500 }
      );
    }

    // Get user context from IAP for logging
    const userInfo = getUserFromIAPHeaders(request);
    
    // Example: Call another Cloud Run service endpoint
    const serviceEndpoint = `${targetServiceUrl}/api/some-endpoint`;
    
    console.info(`Making service-to-service request to ${serviceEndpoint} for user ${userInfo.email}`);
    
    // Use the service-to-service authentication function (uses ID tokens)
    const response = await callCloudRunService(
      serviceEndpoint,
      {
        method: 'POST',
        body: JSON.stringify({ message })
      },
      userInfo.email
    );
    
    const data = await response.json();
    
    return NextResponse.json({
      success: true,
      response: data,
      targetService: serviceEndpoint
    });
    
  } catch (error) {
    console.error('Error in service-to-service call:', error);
    return NextResponse.json(
      { 
        error: 'Service-to-service call failed',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
