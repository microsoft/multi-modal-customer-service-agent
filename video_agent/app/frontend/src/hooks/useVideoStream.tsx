// hooks/useVideoStream.tsx  
import { useRef, useEffect } from "react";  
  
interface UseVideoStreamParams {  
  startMedia: () => Promise<MediaStream>;  
  frameInterval?: number;  
  onFrame: (frameData: string) => void;  
}  
  
export function useVideoStream({ startMedia, frameInterval = 900, onFrame }: UseVideoStreamParams) {  
  const videoRef = useRef<HTMLVideoElement>(null);  
  const canvasRef = useRef<HTMLCanvasElement>(document.createElement("canvas"));  
  const mediaStreamRef = useRef<MediaStream | null>(null);  
  const activeRef = useRef(false);  
  const frameTimeoutRef = useRef<number | null>(null);  
  
  async function start() {  
    mediaStreamRef.current = await startMedia();  
    if (videoRef.current) {  
      videoRef.current.srcObject = mediaStreamRef.current;  
      await videoRef.current.play();  
    }  
    activeRef.current = true;  
    captureFrames();  
  }  
  
  async function captureFrames() {  
    if (!activeRef.current || !videoRef.current) return;  
    const canvas = canvasRef.current;  
    const context = canvas.getContext("2d");  
    if (context) {  
      canvas.width = videoRef.current.videoWidth;  
      canvas.height = videoRef.current.videoHeight;  
      context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);  
      const frameData = canvas.toDataURL("image/jpeg");  
      onFrame(frameData);  
    }  
    frameTimeoutRef.current = window.setTimeout(captureFrames, frameInterval);  
  }  
  
  function stop() {  
    activeRef.current = false;  
    if (frameTimeoutRef.current) clearTimeout(frameTimeoutRef.current);  
    if (mediaStreamRef.current) {  
      mediaStreamRef.current.getTracks().forEach(track => track.stop());  
    }  
    if (videoRef.current) {  
      videoRef.current.pause();  
      videoRef.current.srcObject = null;  
    }  
  }  
  
  useEffect(() => {  
    return () => {  
      stop();  
    };  
  }, []);  
  
  return { videoRef, start, stop };  
}  

export async function sendFrame(frameData: string) {  
    const sessionKey = localStorage.getItem("session_state_key");  
    if (!sessionKey) {  
      console.error("Session state key is missing");  
      return;  
    }  
    
    try {  
      const response = await fetch("/api/upload_video_frame", {  
        method: "POST",  
        headers: { "Content-Type": "application/json" },  
        body: JSON.stringify({ frame: frameData, session_state_key: sessionKey }),  
      });  
    
      if (!response.ok) {  
        throw new Error(`Error: ${response.statusText}`);  
      }  
    } catch (error) {  
      console.error("Failed to send frame:", error);  
    }  
  }  
  