import { useState, useRef } from "react";  
import { Mic, MicOff, Video, VideoOff, Monitor, MonitorOff } from "lucide-react"; // Add Monitor and MonitorOff icons  
import { Button } from "@/components/ui/button";  
import { GroundingFiles } from "@/components/ui/grounding-files";  
import GroundingFileView from "@/components/ui/grounding-file-view";  
import StatusMessage from "@/components/ui/status-message";  
import useRealTime from "@/hooks/useRealtime";  
import useAudioRecorder from "@/hooks/useAudioRecorder";  
import useAudioPlayer from "@/hooks/useAudioPlayer";  
import { GroundingFile, ToolResult } from "./types";  
import logo from "./assets/logo.svg";  
  
function App() {  
  const [isRecording, setIsRecording] = useState(false);  
  const [isVideoOn, setIsVideoOn] = useState(false); // Video state  
  const [isScreenSharing, setIsScreenSharing] = useState(false); // Screen sharing state  
  const [groundingFiles, setGroundingFiles] = useState<GroundingFile[]>([]);  
  const [selectedFile, setSelectedFile] = useState<GroundingFile | null>(null);  
  const [inputText, setInputText] = useState(""); // State for the text box input  
  
  const videoRef = useRef<HTMLVideoElement>(null); // Reference to video element  
  const mediaStreamRef = useRef<MediaStream | null>(null); // Media stream reference  
  
  const { startSession, addUserMessage, addUserAudio, inputAudioBufferClear } = useRealTime({  
    enableInputAudioTranscription: true,  
    onWebSocketOpen: () => console.log("WebSocket connection opened"),  
    onWebSocketClose: () => console.log("WebSocket connection closed"),  
    onWebSocketError: (event) => console.error("WebSocket error:", event),  
    onReceivedError: (message) => console.error("error", message),  
    onReceivedResponseAudioDelta: (message) => {  
      isRecording && playAudio(message.delta);  
    },  
    onReceivedInputAudioBufferSpeechStarted: () => {  
      stopAudioPlayer();  
    },  
    onReceivedExtensionMiddleTierToolResponse: (message) => {  
      const result: ToolResult = JSON.parse(message.tool_result);  
      const files: GroundingFile[] = result.sources.map((x) => {  
        const match = x.chunk_id.match(/_pages_(\d+)$/);  
        const name = match ? `${x.title}#page=${match[1]}` : x.title;  
        return { id: x.chunk_id, name: name, content: x.chunk };  
      });  
      setGroundingFiles((prev) => [...prev, ...files]);  
    },  
  });  
  
  const { reset: resetAudioPlayer, play: playAudio, stop: stopAudioPlayer } = useAudioPlayer();  
  const { start: startAudioRecording, stop: stopAudioRecording } = useAudioRecorder({  
    onAudioRecorded: addUserAudio,  
  });  
  
  const onToggleListening = async () => {  
    if (!isRecording) {  
      startSession();  
      await startAudioRecording();  
      resetAudioPlayer();  
      setIsRecording(true);  
    } else {  
      await stopAudioRecording();  
      stopAudioPlayer();  
      inputAudioBufferClear();  
      setIsRecording(false);  
    }  
  };  
  
  const videoActiveRef = useRef(false);  
  
  const onToggleVideo = async () => {  
    if (!isVideoOn) {  
      videoActiveRef.current = true;  
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });  
      mediaStreamRef.current = stream;  
      if (videoRef.current) {  
        videoRef.current.srcObject = stream;  
        await videoRef.current.play();  
      }  
  
      const sendVideoFrames = async () => {  
        const videoCanvas = document.createElement("canvas");  
        const videoContext = videoCanvas.getContext("2d");  
        if (!videoContext) return;  
  
        const sessionKey = localStorage.getItem("session_state_key");  
        console.log("session_state_key in video", sessionKey);  
  
        const intervalId = setInterval(async () => {  
          if (!videoActiveRef.current) {  
            clearInterval(intervalId);  
            return;  
          }  
          if (videoRef.current) {  
            videoCanvas.width = videoRef.current.videoWidth;  
            videoCanvas.height = videoRef.current.videoHeight;  
            videoContext.drawImage(  
              videoRef.current,  
              0,  
              0,  
              videoCanvas.width,  
              videoCanvas.height  
            );  
            const frameData = videoCanvas.toDataURL("image/jpeg");  
            await fetch("/api/upload_video_frame", {  
              method: "POST",  
              headers: { "Content-Type": "application/json" },  
              body: JSON.stringify({  
                frame: frameData,  
                session_state_key: sessionKey,  
              }),  
            });  
          }  
        }, 900);  
      };  
  
      sendVideoFrames();  
      setIsVideoOn(true);  
    } else {  
      videoActiveRef.current = false;  
      if (mediaStreamRef.current) {  
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());  
      }  
      if (videoRef.current) {  
        videoRef.current.pause();  
        videoRef.current.srcObject = null;  
      }  
      setIsVideoOn(false);  
    }  
  };  
  
  const screenSharingActiveRef = useRef(false); // Ref to track screen sharing state  
  
  const onToggleScreenSharing = async () => {  
    if (!isScreenSharing) {  
      // Start screen sharing  
      screenSharingActiveRef.current = true; // Update the ref immediately  
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });  
      mediaStreamRef.current = stream;  
      if (videoRef.current) {  
        videoRef.current.srcObject = stream;  
        await videoRef.current.play();  
      }  
    
      // Send screen frames to backend using an interval  
      const sendScreenFrames = async () => {  
        const videoCanvas = document.createElement("canvas");  
        const videoContext = videoCanvas.getContext("2d");  
        if (!videoContext) return;  
    
        const sessionKey = localStorage.getItem("session_state_key"); // Retrieve the session_state_key  
        console.log("session_state_key in screen sharing", sessionKey);  
    
        const intervalId = setInterval(async () => {  
          if (!screenSharingActiveRef.current) {  
            // Check the ref instead of the state variable  
            clearInterval(intervalId);  
            return;  
          }  
          if (videoRef.current) {  
            videoCanvas.width = videoRef.current.videoWidth;  
            videoCanvas.height = videoRef.current.videoHeight;  
            videoContext.drawImage(  
              videoRef.current,  
              0,  
              0,  
              videoCanvas.width,  
              videoCanvas.height  
            );  
            const frameData = videoCanvas.toDataURL("image/jpeg");  
            await fetch("/api/upload_video_frame", {  
              method: "POST",  
              headers: { "Content-Type": "application/json" },  
              body: JSON.stringify({  
                frame: frameData,  
                session_state_key: sessionKey,  
              }),  
            });  
          }  
        }, 900); // Send frames every 900ms  
      };  
    
      sendScreenFrames();  
      setIsScreenSharing(true); // Update the state  
    } else {  
      // Stop screen sharing  
      screenSharingActiveRef.current = false; // Update the ref immediately  
      if (mediaStreamRef.current) {  
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());  
      }  
      if (videoRef.current) {  
        videoRef.current.pause();  
        videoRef.current.srcObject = null;  
      }  
      setIsScreenSharing(false); // Update the state  
    }  
  };    
  const onSendText = () => {  
    if (inputText.trim()) {  
      addUserMessage(inputText.trim());  
      setInputText("");  
    }  
  };  
  
  return (  
    <div className="flex min-h-screen flex-col text-gray-900" style={{ backgroundColor: "transparent" }}>  
      <div className="p-4 sm:absolute sm:left-4 sm:top-4">  
        <img src={logo} alt="Azure logo" className="h-16 w-16" />  
      </div>  
      <main className="flex flex-grow flex-col items-center justify-center">  
        <h1 className="mb-8 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-4xl font-bold text-transparent md:text-7xl">  
          AI Customer Service  
        </h1>  
        <div className="mb-4 flex flex-col items-center justify-center">  
          <Button  
            onClick={onToggleListening}  
            className={`h-12 w-60 ${isRecording ? "bg-red-600 hover:bg-red-700" : "bg-purple-500 hover:bg-purple-600"}`}  
            aria-label={isRecording ? "Stop recording" : "Start recording"}  
          >  
            {isRecording ? (  
              <>  
                <MicOff className="mr-2 h-4 w-4" />  
                Stop conversation  
              </>  
            ) : (  
              <>  
                <Mic className="mr-2 h-6 w-6" />  
                Start conversation  
              </>  
            )}  
          </Button>  
          <Button  
            onClick={onToggleVideo}  
            className={`mt-4 h-12 w-60 ${isVideoOn ? "bg-red-600 hover:bg-red-700" : "bg-blue-500 hover:bg-blue-600"}`}  
            aria-label={isVideoOn ? "Stop video" : "Start video"}  
          >  
            {isVideoOn ? (  
              <>  
                <VideoOff className="mr-2 h-4 w-4" />  
                Stop video  
              </>  
            ) : (  
              <>  
                <Video className="mr-2 h-6 w-6" />  
                Start video  
              </>  
            )}  
          </Button>  
          <Button  
            onClick={onToggleScreenSharing}  
            className={`mt-4 h-12 w-60 ${isScreenSharing ? "bg-red-600 hover:bg-red-700" : "bg-green-500 hover:bg-green-600"}`}  
            aria-label={isScreenSharing ? "Stop screen sharing" : "Start screen sharing"}  
          >  
            {isScreenSharing ? (  
              <>  
                <MonitorOff className="mr-2 h-4 w-4" />  
                Stop screen sharing  
              </>  
            ) : (  
              <>  
                <Monitor className="mr-2 h-6 w-6" />  
                Start screen sharing  
              </>  
            )}  
          </Button>  
          <StatusMessage isRecording={isRecording} />  
        </div>  
        <div className="mt-4 flex items-center space-x-4">  
          <input  
            type="text"  
            value={inputText}  
            onChange={(e) => setInputText(e.target.value)}  
            placeholder="Type your message..."  
            className="w-60 rounded-md border border-gray-300 p-2"  
          />  
          <Button onClick={onSendText} className="bg-blue-500 hover:bg-blue-600">  
            Send  
          </Button>  
        </div>  
        <GroundingFiles files={groundingFiles} onSelected={setSelectedFile} />  
        <video ref={videoRef} className="mt-4" style={{ width: "300px", height: "200px" }} />  
      </main>  
      <footer className="py-4 text-center">  
        <p>Built with Azure & OpenAI</p>  
      </footer>  
      <GroundingFileView groundingFile={selectedFile} onClosed={() => setSelectedFile(null)} />  
    </div>  
  );  
}  
  
export default App;  