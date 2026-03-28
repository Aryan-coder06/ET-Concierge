"use client";

import { useRef, useState } from "react";

const REST_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL 
    ? `${process.env.NEXT_PUBLIC_API_BASE_URL}/chat/voice` 
    : "http://127.0.0.1:8000/chat/voice";

export function VoiceChatButton({ threadId }: { threadId: string }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState("");
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);

  const playAudio = async (base64Audio: string) => {
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
      source.start(0);
    } catch (e) {
      console.error("Error decoding audio", e);
    }
  };

  const startRecording = async () => {
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
        console.log("Recording stopped. Blob size:", audioBlob.size, "type:", audioBlob.type);
        if (audioBlob.size > 0) {
          await sendAudioToBackend(audioBlob);
        } else {
          console.warn("Empty audio blob, skipping backend call.");
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
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
      setIsProcessing(true);
      setStatusText("Processing...");
    }
  };

  const sendAudioToBackend = async (blob: Blob) => {
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
      
      if (data.audio) {
        setStatusText("Speaking...");
        await playAudio(data.audio);
      }
      
      setStatusText("");
    } catch (err: any) {
      console.error("Error sending audio", err);
      setStatusText("Error: " + err.message);
    } finally {
      setIsProcessing(false);
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
