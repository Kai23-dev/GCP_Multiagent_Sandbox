#!/usr/bin/env node

console.log('OAuth Configuration Verification');
console.log('================================\n');

// Check environment variables
const clientId = process.env.OAUTH_CLIENT_ID;
const clientSecret = process.env.OAUTH_CLIENT_SECRET;

console.log('Environment Variables:');
console.log('----------------------');
console.log(`OAUTH_CLIENT_ID: ${clientId ? '✓ Set' : '✗ Not set'}`);
console.log(`OAUTH_CLIENT_SECRET: ${clientSecret ? '✓ Set (hidden)' : '✗ Not set'}`);

if (clientId) {
  console.log(`\nClient ID: ${clientId}`);
}

console.log('\n\nRequired Google Cloud Console Configuration:');
console.log('-------------------------------------------');
console.log('\n1. Go to: https://console.cloud.google.com/apis/credentials');
console.log(`2. Find OAuth 2.0 Client ID: ${clientId || '[YOUR_CLIENT_ID]'}`);
console.log('3. Click to edit and add these Authorized JavaScript origins:\n');

const ports = [3000, 3001, 3002, 3003];
const origins = [];

ports.forEach(port => {
  origins.push(`http://localhost:${port}`);
  origins.push(`http://127.0.0.1:${port}`);
});

origins.forEach(origin => {
  console.log(`   • ${origin}`);
});

console.log('\n4. Save the changes and wait 5-10 minutes for propagation');

console.log('\n\nCurrent Development Server:');
console.log('---------------------------');
console.log('The dev server will try ports in order: 3000, 3001, 3002, 3003');
console.log('Make sure all these ports are added to your OAuth configuration!\n');

console.log('\nTo add these origins:');
console.log('1. Open https://console.cloud.google.com/apis/credentials');
console.log(`2. Click on your OAuth 2.0 Client ID (${clientId ? clientId.split('.')[0] + '...' : 'your-client-id'})`);
console.log('3. Under "Authorized JavaScript origins", add each origin listed above');
console.log('4. Click "SAVE" at the bottom');
console.log('5. Wait 5-10 minutes for changes to propagate');
console.log('6. Clear your browser cache and try signing in again');