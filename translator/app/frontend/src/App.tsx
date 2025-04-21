import { useState, useEffect } from "react";  
import { Mic, MicOff, Clipboard, Check } from "lucide-react"; // Add Check icon  
import { Button } from "@/components/ui/button";  
import StatusMessage from "@/components/ui/status-message";  
import useRealTime from "@/hooks/useRealtime";  
import useAudioRecorder from "@/hooks/useAudioRecorder";  
import useAudioPlayer from "@/hooks/useAudioPlayer";  
import logo from "./assets/logo.svg";  
  
const SUPPORTED_LANGUAGES = [  
  { code: "en", name: "English" },  
  { code: "es", name: "Spanish" },  
  { code: "fr", name: "French" },  
  { code: "vi", name: "Vietnamese" },  
  { code: "de", name: "German" },  
  { code: "ja", name: "Japanese" }, 
  { code: "ko", name: "Korean" },
{ code: "zh", name: "Chinese" },
{ code: "pt", name: "Portuguese" },
{ code: "ar", name: "Arabic" },
{ code: "ru", name: "Russian" },
{ code: "it", name: "Italian" },
{ code: "tr", name: "Turkish" },
{ code: "pl", name: "Polish" },
{ code: "nl", name: "Dutch" },
{ code: "sv", name: "Swedish" },
{ code: "da", name: "Danish" },
{ code: "fi", name: "Finnish" },
{ code: "no", name: "Norwegian" },
{ code: "cs", name: "Czech" },
{ code: "hu", name: "Hungarian" },
{ code: "ro", name: "Romanian" },
{ code: "sk", name: "Slovak" },
{ code: "bg", name: "Bulgarian" },
{ code: "el", name: "Greek" },
{ code: "th", name: "Thai" },
{ code: "id", name: "Indonesian" },
{ code: "hi", name: "Hindi" },
{ code: "he", name: "Hebrew" },
{ code: "ms", name: "Malay" },


];  
  
function App() {  
  const [isRecording, setIsRecording] = useState(false);  
  const [sessionKey, setSessionKey] = useState("");  
  const [isNewSession] = useState(true);  
  const [userLang, setUserLang] = useState("en");  
  const [partnerLang, setPartnerLang] = useState("");  
  const [isSessionReady, setIsSessionReady] = useState(false);  
  const [connectionError, setConnectionError] = useState("");  
  const [joinCode, setJoinCode] = useState("");  
  const [isCopied, setIsCopied] = useState(false); // State to track copy status  
  
  const { stop: stopAudioPlayer, reset: resetAudioPlayer, play: playAudio } = useAudioPlayer();  
  
  // Polling to check if the session is ready  
  useEffect(() => {  
    if (!sessionKey || isSessionReady) return;  
  
    const intervalId = setInterval(async () => {  
      try {  
        const resp = await fetch(  
          `/handshake?action=status&session_key=${encodeURIComponent(sessionKey)}&user_lang=${encodeURIComponent(userLang)}`  
        );  
        const data = await resp.json();  
        if (data.status === "ok" && data.ready) {  
          setIsSessionReady(true);  
          if (data.partner_lang) {  
            setPartnerLang(data.partner_lang);  
          }  
        } else if (data.status !== "ok") {  
          setConnectionError(data.error || "Error checking session status");  
        }  
      } catch (err) {  
        console.error("Polling error:", err);  
        setConnectionError("Failed to poll session status");  
      }  
    }, 2000);  
  
    return () => clearInterval(intervalId);  
  }, [sessionKey, isSessionReady]);  
  
  const {  
    startSession,  
    addUserAudio,  
    inputAudioBufferClear,  
  } = useRealTime({  
    sessionKey: isSessionReady ? sessionKey : "",  
    user_lang: userLang,  
    enableInputAudioTranscription: true,  
    onWebSocketOpen: () => console.log("WebSocket connection opened"),  
    onWebSocketClose: () => console.log("WebSocket connection closed"),  
    onWebSocketError: (event) => console.error("WebSocket error:", event),  
    onReceivedError: (message) => console.error("Error:", message),  
    onReceivedResponseAudioDelta: (message) => {  
      if (isRecording) playAudio(message.delta);  
    },  
    onReceivedInputAudioBufferSpeechStarted: () => {  
      stopAudioPlayer();  
    },  
  });  
  
  const { start: startAudioRecording, stop: stopAudioRecording } = useAudioRecorder({  
    onAudioRecorded: addUserAudio,  
  });  
  
  const handleCreateSession = async () => {  
    setConnectionError("");  
    try {  
      const resp = await fetch(  
        `/handshake?action=create&user_lang=${encodeURIComponent(userLang)}`  
      );  
      const data = await resp.json();  
      if (data.status === "ok" && data.session_key) {  
        setSessionKey(data.session_key);  
        setIsSessionReady(data.ready ?? false);  
        setPartnerLang(data.partner_lang ?? "");  
      } else {  
        setConnectionError(data.error || "Failed to create session");  
      }  
    } catch (err) {  
      console.error(err);  
      setConnectionError("Failed to create session");  
    }  
  };  
  
  const handleJoinSession = async () => {  
    setConnectionError("");  
    try {  
      const resp = await fetch(  
        `/handshake?action=join&session_key=${encodeURIComponent(joinCode)}&user_lang=${encodeURIComponent(userLang)}`  
      );  
      const data = await resp.json();  
      if (data.status === "ok") {  
        setSessionKey(data.session_key || "");  
        setIsSessionReady(data.ready ?? false);  
        setPartnerLang(data.partner_lang ?? "");  
      } else {  
        setConnectionError(data.error || "Failed to join session");  
      }  
    } catch (err) {  
      console.error(err);  
      setConnectionError("Failed to join session");  
    }  
  };  
  
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
  
  const copyToClipboard = () => {  
    if (sessionKey) {  
      navigator.clipboard.writeText(sessionKey)  
        .then(() => setIsCopied(true)) // Set copied state to true  
        .catch((err) => console.error("Failed to copy session code", err));  
    }  
  };  
  
  return (  
    <div className="flex min-h-screen flex-col text-gray-900" style={{ backgroundColor: "transparent" }}>  
      <div className="p-4 sm:absolute sm:left-4 sm:top-4">  
        <img src={logo} alt="Azure logo" className="h-16 w-16" />  
      </div>  
      <main className="flex flex-grow flex-col items-center justify-center">  
        <h1 className="mb-8 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-4xl font-bold text-transparent md:text-7xl">  
          AI Translator  
        </h1>  
        {!sessionKey ? (  
          <div className="mb-4">  
            <label>Select Your Language</label>  
            <select  
              value={userLang}  
              onChange={(e) => setUserLang(e.target.value)}  
              className="p-2 border rounded w-full mb-4"  
            >  
              {SUPPORTED_LANGUAGES.map((lang) => (  
                <option key={lang.code} value={lang.code}>  
                  {lang.name}  
                </option>  
              ))}  
            </select>  
            <Button onClick={handleCreateSession} className="mr-2">  
              Create New Session  
            </Button>  
            <Button onClick={handleJoinSession}>Join Existing Session</Button>  
            <input  
              type="text"  
              value={joinCode}  
              onChange={(e) => setJoinCode(e.target.value)}  
              placeholder="Enter Session Code"  
              className="p-2 border rounded w-full mt-2"  
            />  
            {connectionError && <p className="text-red-500 mt-2">{connectionError}</p>}  
          </div>  
        ) : (  
          <div className="mb-4 flex flex-col items-center justify-center">  
            <h2 className="text-white font-bold">{isNewSession ? "Your Session Code:" : "Joined Session:"}</h2>  
            <div className="flex items-center">  
              <p className="mr-2">{sessionKey}</p>  
              <Button onClick={copyToClipboard} className="flex items-center">  
                {isCopied ? <Check className="mr-1" /> : <Clipboard className="mr-1" />}  
                {isCopied ? "Copied" : "Copy"}  
              </Button>  
            </div>  
            {!isSessionReady ? (  
              <p className="text-white font-bold">Waiting for partner to join...</p>  
            ) : (  
              <p className="text-white font-bold">  
                Session Active: You speak{" "}  
                {SUPPORTED_LANGUAGES.find((l) => l.code === userLang)?.name}, and your partner speaks{" "}  
                {SUPPORTED_LANGUAGES.find((l) => l.code === partnerLang)?.name}.  
              </p>  
            )}  
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
            {connectionError && <p className="text-red-500 mt-2">{connectionError}</p>}  
            <StatusMessage isRecording={isRecording} />  
          </div>  
        )}  
      </main>  
      <footer className="py-4 text-center">  
        <p>Built with Azure & OpenAI</p>  
      </footer>  
    </div>  
  );  
}  
  
export default App;  