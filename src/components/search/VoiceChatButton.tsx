"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getApiBaseUrl } from "@/lib/api-base-url";

type VoiceChatButtonProps = {
  threadId: string;
  disabled?: boolean;
  onError?: (message: string) => void;
  onBusyChange?: (busy: boolean) => void;
  onResponse?: (threadId: string, data: unknown) => void;
};

type BrowserAudioContext = Window &
  typeof globalThis & {
    webkitAudioContext?: typeof AudioContext;
  };

function MicIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M8.25 4.5a3.75 3.75 0 1 1 7.5 0v8.25a3.75 3.75 0 1 1-7.5 0V4.5Z" />
      <path d="M6 10.5a.75.75 0 0 1 .75.75v1.5a5.25 5.25 0 1 0 10.5 0v-1.5a.75.75 0 0 1 1.5 0v1.5a6.75 6.75 0 0 1-6 6.71v2.29h3a.75.75 0 0 1 0 1.5h-7.5a.75.75 0 0 1 0-1.5h3v-2.29a6.75 6.75 0 0 1-6-6.71v-1.5A.75.75 0 0 1 6 10.5Z" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
  );
}

export function VoiceChatButton({
  threadId,
  disabled = false,
  onError,
  onBusyChange,
  onResponse,
}: VoiceChatButtonProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const busy = disabled || isRecording || isProcessing;

  useEffect(() => {
    onBusyChange?.(busy);
  }, [busy, onBusyChange]);

  const stopSpeaking = useCallback(() => {
    if (!audioSourceRef.current) return;
    try {
      audioSourceRef.current.stop();
    } catch {
      // already stopped
    }
    audioSourceRef.current = null;
    setStatusText("");
  }, []);

  const playAudio = useCallback(
    async (base64Audio: string) => {
      stopSpeaking();
      const browserWindow = window as BrowserAudioContext;
      const AudioCtor = browserWindow.AudioContext || browserWindow.webkitAudioContext;
      if (!AudioCtor) return;

      if (!audioContextRef.current) {
        audioContextRef.current = new AudioCtor();
      }

      const binary = window.atob(base64Audio);
      const bytes = new Uint8Array(binary.length);
      for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
      }

      try {
        const buffer = await audioContextRef.current.decodeAudioData(bytes.buffer.slice(0));
        const source = audioContextRef.current.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContextRef.current.destination);
        source.onended = () => {
          if (audioSourceRef.current === source) {
            audioSourceRef.current = null;
            setStatusText("");
          }
        };
        audioSourceRef.current = source;
        setStatusText("Speaking...");
        source.start(0);
      } catch (error) {
        console.error("Voice playback failed", error);
        setStatusText("");
      }
    },
    [stopSpeaking]
  );

  const sendAudio = useCallback(
    async (blob: Blob, mimeType: string) => {
      const apiBaseUrl = getApiBaseUrl();
      if (!apiBaseUrl) {
        onError?.("Voice is unavailable because the backend URL is missing.");
        setIsProcessing(false);
        setStatusText("");
        return;
      }

      const formData = new FormData();
      formData.append("audio_file", blob, `recording.${mimeType.includes("ogg") ? "ogg" : mimeType.includes("webm") ? "webm" : "wav"}`);
      formData.append("thread_id", threadId);

      try {
        const response = await fetch(`${apiBaseUrl}/chat/voice`, {
          method: "POST",
          body: formData,
        });

        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            typeof payload?.detail === "string" ? payload.detail : `Voice request failed with ${response.status}`
          );
        }

        onResponse?.(threadId, payload);

        if (typeof payload?.audio === "string" && payload.audio.trim()) {
          await playAudio(payload.audio);
        } else {
          setStatusText("");
        }
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Voice request failed unexpectedly.";
        onError?.(message);
        setStatusText("");
      } finally {
        setIsProcessing(false);
      }
    },
    [onError, onResponse, playAudio, threadId]
  );

  const stopRecording = useCallback(() => {
    if (!mediaRecorderRef.current || !isRecording) return;
    mediaRecorderRef.current.stop();
    mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
    setIsRecording(false);
    setIsProcessing(true);
    setStatusText("Processing...");
  }, [isRecording]);

  const startRecording = useCallback(async () => {
    if (busy) return;
    if (!navigator.mediaDevices?.getUserMedia) {
      onError?.("Your browser does not support microphone access here.");
      return;
    }

    stopSpeaking();
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeTypes = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ];
      const supportedMimeType =
        mimeTypes.find((item) => MediaRecorder.isTypeSupported(item)) || "";

      const recorder = supportedMimeType
        ? new MediaRecorder(stream, { mimeType: supportedMimeType })
        : new MediaRecorder(stream);

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || supportedMimeType || "audio/webm",
        });
        if (blob.size === 0) {
          setIsProcessing(false);
          setStatusText("");
          return;
        }

        await sendAudio(blob, recorder.mimeType || supportedMimeType || "audio/webm");
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
      setStatusText("Listening...");
    } catch (error) {
      console.error("Microphone access failed", error);
      onError?.("Microphone access failed. Please allow mic permissions and retry.");
      setStatusText("");
      setIsRecording(false);
    }
  }, [busy, onError, sendAudio, stopSpeaking]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      }
      stopSpeaking();
    };
  }, [stopSpeaking]);

  return (
    <div className="flex flex-col items-end gap-1.5">
      <button
        type="button"
        onClick={isRecording ? stopRecording : startRecording}
        disabled={disabled || isProcessing}
        className={`inline-flex h-11 w-11 items-center justify-center border-2 border-black shadow-[4px_4px_0px_0px_black] transition-all ${
          isRecording
            ? "bg-[#D02020] text-white animate-pulse"
            : statusText === "Speaking..."
              ? "bg-black text-white"
              : "bg-[#F0C020] text-black hover:-translate-y-0.5"
        } ${disabled || isProcessing ? "cursor-not-allowed opacity-60" : ""}`}
        title={isRecording ? "Stop recording" : "Record voice message"}
      >
        {isRecording || statusText === "Speaking..." ? <StopIcon /> : <MicIcon />}
      </button>

      <span className="min-h-[14px] text-right text-[9px] font-black uppercase tracking-[0.16em] text-black/55">
        {statusText}
      </span>
    </div>
  );
}
