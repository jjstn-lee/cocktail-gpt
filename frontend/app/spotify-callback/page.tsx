'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function SpotifyCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState('Processing...');
  const [isError, setIsError] = useState(false);

  console.log('[SPOTIFY_CALLBACK] Component mounted!');
  console.log('[SPOTIFY_CALLBACK] Location:', typeof window !== 'undefined' ? window.location.href : 'N/A');

  useEffect(() => {
    const status = searchParams.get('status');
    const reason = searchParams.get('reason');

    console.log('[SPOTIFY_CALLBACK] Page loaded');
    console.log('[SPOTIFY_CALLBACK] URL:', window.location.href);
    console.log('[SPOTIFY_CALLBACK] status param:', status);
    console.log('[SPOTIFY_CALLBACK] reason param:', reason);

    if (status === 'success') {
      console.log('[SPOTIFY_CALLBACK] ✓ Success detected, redirecting in 2s');
      setMessage('Spotify connected successfully! Redirecting...');
      setIsError(false);
      const timer = setTimeout(() => {
        console.log('[SPOTIFY_CALLBACK] Redirecting to home');
        router.push('/');
      }, 2000);
      return () => clearTimeout(timer);
    } else {
      console.log('[SPOTIFY_CALLBACK] ✗ Error detected or no status');
      setMessage(`Connection failed: ${reason || 'Unknown error'}`);
      setIsError(true);
      const timer = setTimeout(() => {
        console.log('[SPOTIFY_CALLBACK] Redirecting to home after error');
        router.push('/');
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0f0f0f]">
      <div className="text-center space-y-6 animate-in fade-in duration-500">
        <div className="text-6xl">
          {isError ? '⚠️' : '✨'}
        </div>
        <h1 className="text-3xl font-semibold text-[#f5f5f5]">
          {isError ? 'Connection Failed' : 'Spotify Connected'}
        </h1>
        <p className={`text-lg ${isError ? 'text-red-400' : 'text-[#d97706]'}`}>
          {message}
        </p>
        <p className="text-sm text-[#808080]">Redirecting you shortly...</p>
      </div>
    </div>
  );
}

export default function SpotifyCallbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-[#0f0f0f]"><p className="text-[#f5f5f5]">Loading...</p></div>}>
      <SpotifyCallbackContent />
    </Suspense>
  );
}
