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
      console.log('[SPOTIFY_CALLBACK] ✓ Success detected, redirecting to profile in 2s');
      setMessage('Spotify connected successfully! Redirecting to profile...');
      setIsError(false);
      // Auto-redirect after 2 seconds
      const timer = setTimeout(() => {
        console.log('[SPOTIFY_CALLBACK] Pushing to /profile');
        router.push('/profile');
      }, 2000);
      return () => clearTimeout(timer);
    } else {
      console.log('[SPOTIFY_CALLBACK] ✗ Error detected or no status');
      setMessage(`Connection failed: ${reason || 'Unknown error'}`);
      setIsError(true);
      // Auto-redirect after 3 seconds
      const timer = setTimeout(() => {
        console.log('[SPOTIFY_CALLBACK] Pushing to /profile after error');
        router.push('/profile');
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4 text-white">
          {isError ? '❌ Connection Failed' : '✅ Spotify Connected'}
        </h1>
        <p className={`text-lg mb-4 ${isError ? 'text-red-400' : 'text-green-400'}`}>
          {message}
        </p>
        <p className="text-sm text-gray-400">Redirecting to profile...</p>
      </div>
    </div>
  );
}

export default function SpotifyCallbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-gray-900"><p className="text-white">Loading...</p></div>}>
      <SpotifyCallbackContent />
    </Suspense>
  );
}
