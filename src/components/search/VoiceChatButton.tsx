"use client";

import { useEffect, useRef, useState } from "react";

const WS_URL =
  process.env.NEXT_PUBLIC_WS_BASE_URL || "ws://127.0.0.1:8000/ws/voice";

export function VoiceChatButton({ threadId }: { threadId: string }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState("");
  
  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const nextTimeRef = useRef<number>(0);
  
  // Set up WebSocket connection
  useEffect(() => {
    // We only connect when the user wants to use voice
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }
    
    wsRef.current = new WebSocket(WS_URL);
    
    wsRef.current.onopen = () => {
      console.log("Voice WebSocket connected");
    };
    
    wsRef.current.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.event === "status") {
          setStatusText(data.message);
        } else if (data.event === "audio") {
          // Play the audio chunk immediately
          playAudioChunk(data.audio);
        } else if (data.event === "turn_complete") {
          setIsProcessing(false);
          setStatusText("");
        } else if (data.event === "error") {
          setStatusText("Error: " + data.message);
          setIsProcessing(false);
        }
      } catch (err) {
        // Not a JSON message, or JSON parse failed
      }
    };
    
    wsRef.current.onclose = () => {
      console.log("Voice WebSocket disconnected");
      setIsProcessing(false);
    };
  };

  const playAudioChunk = async (base64Audio: string) => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      nextTimeRef.current = audioContextRef.current.currentTime;
    }
    
    const audioCtx = audioContextRef.current;
    
    // Decode base64 to array buffer
    const binaryString = window.atob(base64Audio);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    
    try {
      const audioBuffer = await audioCtx.decodeAudioData(bytes.buffer);
      const source = audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioCtx.destination);
      
      // Schedule playback to be contiguous
      const playTime = Math.max(audioCtx.currentTime, nextTimeRef.current);
      source.start(playTime);
      nextTimeRef.current = playTime + audioBuffer.duration;
      
    } catch (e) {
      console.error("Error decoding audio chunk", e);
    }
  };

  const startRecording = async () => {
    connectWebSocket();
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Determine supported MIME type
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
      ];
      
      const supportedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type)) || '';
      console.log("Using MIME type:", supportedMimeType);
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType: supportedMimeType });
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(event.data);
        }
      };
      
      mediaRecorder.start(250); // send chunks every 250ms
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      setStatusText("Listening...");
      
    } catch (err) {
      console.error("Error accessing microphone", err);
      setStatusText("Microphone error");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
      setIsProcessing(true);
      setStatusText("Processing...");
      
      // Tell the server we are done speaking
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          event: "stop_speaking",
          thread_id: threadId
        }));
      }
    }
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onMouseLeave={stopRecording}
        onTouchStart={startRecording}
        onTouchEnd={stopRecording}
        disabled={isProcessing}
        className={`flex h-12 w-12 items-center justify-center rounded-full border-2 border-black transition-all shadow-[2px_2px_0px_0px_black]
          ${isRecording ? 'bg-red-500 text-white scale-105' : 'bg-yellow-400 text-black hover:-translate-y-1 hover:shadow-[4px_4px_0px_0px_black]'}
          ${isProcessing ? 'opacity-50 cursor-not-allowed bg-gray-300' : ''}`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
          <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
          <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
        </svg>
      </button>
      
      {statusText && (
        <span className="text-[10px] font-bold uppercase tracking-wider text-black/60">
          {statusText}
        </span>
      )}
    </div>
  );
}
