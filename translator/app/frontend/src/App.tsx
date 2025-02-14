import { useState } from "react";  
import { Button } from "@/components/ui/button";  
import useRealTime from "@/hooks/useRealtime";  
import useAudioRecorder from "@/hooks/useAudioRecorder";  
import useAudioPlayer from "@/hooks/useAudioPlayer";  
import logo from "./assets/logo.svg";  
  
function App() {  
    const [isRecording, setIsRecording] = useState(false);  
    const [sessionCode, setSessionCode] = useState("");  
    const [isNewSession, setIsNewSession] = useState(true);  
    const [sourceLang, setSourceLang] = useState("en");  
    const [targetLang, setTargetLang] = useState("es");  
  
    const generateSessionCode = () => {  
        return Math.random().toString(36).substring(2, 8).toUpperCase();  
    };  
  
    const handleSessionAction = (createNew: boolean) => {  
        if (createNew) {  
            const newCode = generateSessionCode();  
            setSessionCode(newCode);  
            setIsNewSession(true);  
        } else {  
            setIsNewSession(false);  
        }  
    };  
  
    const { startSession, addUserAudio, inputAudioBufferClear } = useRealTime({  
        sessionKey: sessionCode,  
        sourceLang,  
        targetLang,  
        enableInputAudioTranscription: true,  
        onWebSocketOpen: () => console.log("WebSocket connection opened"),  
        onWebSocketClose: () => console.log("WebSocket connection closed"),  
        onWebSocketError: (event) => console.error("WebSocket error:", event),  
        onReceivedResponseAudioDelta: (message) => {  
            isRecording && playAudio(message.delta);  
        },  
        onReceivedInputAudioBufferSpeechStarted: () => {  
            stopAudioPlayer();  
        },  
    });  
  
    const { reset: resetAudioPlayer, play: playAudio, stop: stopAudioPlayer } = useAudioPlayer();  
    const { start: startAudioRecording, stop: stopAudioRecording } = useAudioRecorder({ onAudioRecorded: addUserAudio });  
  
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
  
    return (  
        <div className="flex min-h-screen flex-col text-gray-900" style={{ backgroundColor: 'transparent' }}>  
            <img src={logo} alt="Azure logo" className="h-12 w-auto mb-4" />  
            <h1 className="mb-8 bg-gradient-to-r from-blue-600 to-green-600 bg-clip-text text-4xl font-bold text-transparent md:text-7xl">  
                Real-Time Translator  
            </h1>  
            <div className="mb-8 flex flex-col items-center gap-4">  
                <div className="flex gap-2">  
                    <Button  
                        onClick={() => handleSessionAction(true)}  
                        className="bg-blue-600 hover:bg-blue-700"  
                    >  
                        Create New Session  
                    </Button>  
                    <span className="self-center">or</span>  
                    <Button  
                        onClick={() => handleSessionAction(false)}  
                        className="bg-green-600 hover:bg-green-700"  
                    >  
                        Join Existing  
                    </Button>  
                </div>  
                {sessionCode && (  
                    <div className="flex flex-col items-center gap-2">  
                        <input  
                            type="text"  
                            placeholder="Enter Session Code"  
                            value={sessionCode}  
                            onChange={(e) => setSessionCode(e.target.value.toUpperCase())}  
                            className="p-2 border rounded text-center uppercase"  
                            pattern="[A-Z0-9]{6}"  
                            maxLength={6}  
                            disabled={isNewSession}  
                        />  
                        {isNewSession && (  
                            <p className="text-sm text-gray-600">  
                                Share this code: {sessionCode}  
                            </p>  
                        )}  
                    </div>  
                )}  
            </div>  
            <div className="flex gap-2 mb-4 justify-center">  
                <select  
                    value={sourceLang}  
                    onChange={(e) => setSourceLang(e.target.value)}  
                    className="p-2 rounded bg-white border"  
                >  
                    <option value="en">English</option>  
                    <option value="es">Spanish</option>  
                    <option value="fr">French</option>  
                </select>  
                <select  
                    value={targetLang}  
                    onChange={(e) => setTargetLang(e.target.value)}  
                    className="p-2 rounded bg-white border"  
                >  
                    <option value="es">Spanish</option>  
                    <option value="en">English</option>  
                    <option value="fr">French</option>  
                </select>  
            </div>  
            <Button  
                onClick={onToggleListening}  
                disabled={!sessionCode}  
                className={`h-12 w-60 ${isRecording ? "bg-red-600" : "bg-purple-500"}`}  
            >  
                {isRecording ? "End Conversation" : "Start Conversation"}  
            </Button>  
        </div>  
    );  
}  
  
export default App;  