import { NextRequest, NextResponse } from 'next/server';
import { getUserFromIAPHeaders } from '@/utils/auth';
import { clearUserSessions, getSessionStats } from '@/utils/session-cache';

export async function POST(request: NextRequest) {
  try {
    // Get user information from IAP headers
    const userInfo = getUserFromIAPHeaders(request);
    
    // Clear all sessions for this user
    await clearUserSessions();
    
    console.log(`Cleared all sessions for user: ${userInfo.userId} (${userInfo.email})`);
    
    return NextResponse.json({
      success: true,
      message: 'All sessions cleared successfully',
      userId: userInfo.userId
    });

  } catch (error) {
    console.error('Error clearing sessions:', error);
    return NextResponse.json(
      { 
        error: 'Failed to clear sessions', 
        details: error instanceof Error ? error.message : 'Unknown error' 
      },
      { status: 500 }
    );
  }
}

export async function GET() {
  try {
    // Get session statistics for debugging
    const stats = getSessionStats();
    
    return NextResponse.json({
      success: true,
      stats
    });

  } catch (error) {
    console.error('Error getting session stats:', error);
    return NextResponse.json(
      { 
        error: 'Failed to get session stats', 
        details: error instanceof Error ? error.message : 'Unknown error' 
      },
      { status: 500 }
    );
  }
}
