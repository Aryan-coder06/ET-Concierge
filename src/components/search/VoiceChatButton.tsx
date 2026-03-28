"use client";

import { useRef, useState, useCallback, useEffect } from "react";

const REST_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL 
    ? `${process.env.NEXT_PUBLIC_API_BASE_URL}/chat/voice` 
    : "http://127.0.0.1:8000/chat/voice";

export function VoiceChatButton({ 
  threadId, 
  onResponse 
}: { 
  threadId: string;
  onResponse?: (userText: string, agentText: string, usedRag?: boolean) => void;
}) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState("");
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const isStartingRef = useRef(false);

  const stopSpeaking = useCallback(() => {
    if (audioSourceRef.current) {
      try {
        audioSourceRef.current.stop();
      } catch (e) {
        // Already stopped or not started
      }
      audioSourceRef.current = null;
    }
  }, []);

  const playAudio = useCallback(async (base64Audio: string) => {
    stopSpeaking();

    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
    
    const audioCtx = audioContextRef.current;
    const binaryString = window.atob(base64Audio);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }
    
    try {
      const audioBuffer = await audioCtx.decodeAudioData(bytes.buffer);
      const source = audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioCtx.destination);
      
      audioSourceRef.current = source;
      source.onended = () => {
        if (audioSourceRef.current === source) {
          audioSourceRef.current = null;
          setStatusText("");
        }
      };

      source.start(0);
    } catch (e) {
      console.error("Error decoding audio", e);
    }
  }, [stopSpeaking]);

  const sendAudioToBackend = useCallback(async (blob: Blob) => {
    const formData = new FormData();
    formData.append("audio_file", blob, "recording.wav");
    formData.append("thread_id", threadId);

    try {
      const response = await fetch(REST_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Backend error: " + response.statusText);
      }

      const data = await response.json();
      
      if (onResponse && data.user_text && data.agent_text) {
        onResponse(data.user_text, data.agent_text, !!data.used_rag);
      }
      
      if (data.audio) {
        setStatusText("Speaking...");
        await playAudio(data.audio);
      } else {
        setStatusText("");
      }
      
    } catch (err: any) {
      console.error("Error sending audio", err);
      setStatusText("Error: " + err.message);
      setTimeout(() => setStatusText(""), 3000);
    } finally {
      setIsProcessing(false);
    }
  }, [threadId, playAudio, onResponse]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
      setIsProcessing(true);
      setStatusText("Processing...");
    }
  }, [isRecording]);

  const startRecording = useCallback(async () => {
    if (isRecording || isProcessing || isStartingRef.current) return;
    
    isStartingRef.current = true;
    stopSpeaking();
    chunksRef.current = [];
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
      ];
      const supportedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type)) || '';
      
      const mediaRecorder = new MediaRecorder(stream, { mimeType: supportedMimeType });
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: supportedMimeType });
        if (audioBlob.size > 0) {
          await sendAudioToBackend(audioBlob);
        } else {
          setIsProcessing(false);
          setStatusText("");
        }
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      setStatusText("Listening...");
    } catch (err) {
      console.error("Error accessing microphone", err);
      setStatusText("Microphone error");
      setIsRecording(false);
    } finally {
      isStartingRef.current = false;
    }
  }, [isRecording, isProcessing, stopSpeaking, sendAudioToBackend]);

  const handleToggle = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else if (statusText === "Speaking...") {
      stopSpeaking();
      setStatusText("");
    } else if (!isProcessing) {
      startRecording();
    }
  }, [isRecording, isProcessing, statusText, stopRecording, stopSpeaking, startRecording]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
      stopSpeaking();
    };
  }, [stopSpeaking]);

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={handleToggle}
        disabled={isProcessing && statusText !== "Speaking..."}
        className={`flex h-12 w-12 items-center justify-center rounded-full border-2 border-black transition-all shadow-[2px_2px_0px_0px_black]
          ${isRecording ? 'bg-red-500 text-white scale-105 animate-pulse' : ''}
          ${statusText === 'Speaking...' ? 'bg-black text-white' : ''}
          ${!isRecording && statusText !== 'Speaking...' ? 'bg-yellow-400 text-black hover:-translate-y-1 hover:shadow-[4px_4px_0px_0px_black]' : ''}
          ${isProcessing && statusText !== "Speaking..." ? 'opacity-50 cursor-not-allowed bg-gray-300' : ''}`}
        title={isRecording ? "Stop recording" : (statusText === "Speaking..." ? "Stop speaking" : "Start recording")}
      >
        {isRecording ? (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
            <path fillRule="evenodd" d="M4.5 7.5a3 3 0 0 1 3-3h9a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3h-9a3 3 0 0 1-3-3v-9Z" clipRule="evenodd" />
          </svg>
        ) : statusText === "Speaking..." ? (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
            <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
            <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.751 6.751 0 0 1-6 6.709v2.291h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.291a6.751 6.751 0 0 1-6-6.709v-1.5A.75.75 0 0 1 6 10.5Z" />
          </svg>
        )}
      </button>
      
      {statusText && (
        <span className="text-[10px] font-bold uppercase tracking-wider text-black/60">
          {statusText}
        </span>
      )}
    </div>
  );
}
