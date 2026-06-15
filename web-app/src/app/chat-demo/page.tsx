'use client';

import { useState } from 'react';
import ChatInterface from '@/components/ChatInterface';
import ChatInterfaceEnhanced from '@/components/ChatInterfaceEnhanced';
import { Sparkles, Zap, Monitor, Smartphone } from 'lucide-react';
import clsx from 'clsx';

export default function ChatDemoPage() {
  const [version, setVersion] = useState<'original' | 'enhanced'>('enhanced');

  return (
    <div className="h-screen flex flex-col">
      {/* Version Switcher Header */}
      <div className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-4 shadow-lg">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center space-x-2">
                <Sparkles className="w-6 h-6" />
                <span>DaVita Chat Interface Comparison</span>
              </h1>
              <p className="text-purple-100 text-sm mt-1">
                Compare the original and enhanced Instagram-inspired interfaces
              </p>
            </div>

            <div className="flex items-center space-x-4">
              <button
                onClick={() => setVersion('original')}
                className={clsx(
                  "px-6 py-3 rounded-xl font-medium transition-all flex items-center space-x-2",
                  version === 'original'
                    ? "bg-white text-purple-600 shadow-lg scale-105"
                    : "bg-white/20 text-white hover:bg-white/30"
                )}
              >
                <Monitor className="w-4 h-4" />
                <span>Original</span>
              </button>

              <button
                onClick={() => setVersion('enhanced')}
                className={clsx(
                  "px-6 py-3 rounded-xl font-medium transition-all flex items-center space-x-2",
                  version === 'enhanced'
                    ? "bg-white text-pink-600 shadow-lg scale-105"
                    : "bg-white/20 text-white hover:bg-white/30"
                )}
              >
                <Smartphone className="w-4 h-4" />
                <span>Enhanced</span>
              </button>
            </div>
          </div>

          {/* Feature highlights */}
          <div className="mt-4 flex flex-wrap gap-2">
            {version === 'enhanced' ? (
              <>
                <FeatureBadge icon={Zap} label="Streaming Responses" />
                <FeatureBadge icon={Sparkles} label="Instagram UI" />
                <FeatureBadge icon="🎮" label="Gamification" />
                <FeatureBadge icon="❤️" label="Reactions" />
                <FeatureBadge icon="🏆" label="Achievements" />
                <FeatureBadge icon="⚡" label="50% Faster" />
              </>
            ) : (
              <>
                <FeatureBadge icon={Monitor} label="Traditional UI" />
                <FeatureBadge icon="💼" label="Professional" />
                <FeatureBadge icon="📝" label="Standard Chat" />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Chat Interface */}
      <div className="flex-1 overflow-hidden">
        {version === 'original' ? <ChatInterface /> : <ChatInterfaceEnhanced />}
      </div>
    </div>
  );
}

function FeatureBadge({ icon, label }: { icon: React.ComponentType<{ className?: string }> | string; label: string }) {
  const Icon = typeof icon === 'string' ? () => <span>{icon}</span> : icon;

  return (
    <div className="inline-flex items-center space-x-1 px-3 py-1 bg-white/20 rounded-full text-xs text-white">
      <Icon className="w-3 h-3" />
      <span>{label}</span>
    </div>
  );
}