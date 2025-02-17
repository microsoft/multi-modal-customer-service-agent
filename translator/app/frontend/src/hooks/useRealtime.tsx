import useWebSocket from "react-use-websocket";  
import {  
  InputAudioBufferAppendCommand,  
  InputAudioBufferClearCommand,  
  Message,  
  ResponseAudioDelta,  
  ResponseAudioTranscriptDelta,  
  ResponseDone,  
  SessionUpdateCommand,  
  ExtensionMiddleTierToolResponse,  
  ResponseInputAudioTranscriptionCompleted,  
} from "@/types";  
  
export type SessionWaitingMessage = Message & {  
  type: "session.waiting";  
  session_key: string;  
  your_lang: string;  
};  
  
export type SessionReadyMessage = Message & {  
  type: "session_ready";  
  session_key: string;  
  your_lang: string;  
  partner_lang: string;  
};  
  
const isSessionWaitingMessage = (message: Message): message is SessionWaitingMessage =>  
  message.type === "session.waiting" && typeof message.session_key === "string";  
  
const isSessionReadyMessage = (message: Message): message is SessionReadyMessage =>  
  message.type === "session_ready" && typeof message.partner_lang === "string";  
  
type Parameters = {  
  sessionKey: string;  
  user_lang: string;  
  enableInputAudioTranscription?: boolean;
  onWebSocketOpen?: () => void;  
  onWebSocketClose?: () => void;  
  onWebSocketError?: (event: Event) => void;  
  onWebSocketMessage?: (event: MessageEvent) => void;  
  onSessionReady?: (partnerLang: string) => void;  
  onSessionWaiting?: (message: SessionWaitingMessage) => void;  
  onReceivedMessage?: (message: Message) => void;  
  onReceivedResponseAudioDelta?: (message: ResponseAudioDelta) => void;  
  onReceivedInputAudioBufferSpeechStarted?: (message: Message) => void;  
  onReceivedResponseDone?: (message: ResponseDone) => void;  
  onReceivedExtensionMiddleTierToolResponse?: (message: ExtensionMiddleTierToolResponse) => void;  
  onReceivedResponseAudioTranscriptDelta?: (message: ResponseAudioTranscriptDelta) => void;  
  onReceivedInputAudioTranscriptionCompleted?: (message: ResponseInputAudioTranscriptionCompleted) => void;  
  onReceivedError?: (message: Message) => void;  
};  
  
export default function useRealTime({  
  sessionKey,  
  user_lang,  
  enableInputAudioTranscription,
  onWebSocketOpen,  
  onWebSocketClose,  
  onWebSocketError,  
  onWebSocketMessage,  
  onSessionReady,  
  onSessionWaiting,  
  onReceivedResponseDone,  
  onReceivedResponseAudioDelta,  
  onReceivedResponseAudioTranscriptDelta,  
  onReceivedInputAudioBufferSpeechStarted,  
  onReceivedExtensionMiddleTierToolResponse,  
  onReceivedInputAudioTranscriptionCompleted,  
  onReceivedError,  
}: Parameters) {  
  const wsEndpoint = `/realtime?session_key=${sessionKey}&user_lang=${user_lang}`;  
  const { sendJsonMessage } = useWebSocket(wsEndpoint, {  
    onOpen: () => onWebSocketOpen?.(),  
    onClose: () => onWebSocketClose?.(),  
    onError: (event) => onWebSocketError?.(event),  
    onMessage: (event) => onMessageReceived(event),  
    shouldReconnect: () => true,  
  });  
  
  const startSession = () => {
    const command: SessionUpdateCommand = {
        type: "session.update",
        session: {
            turn_detection: {
                type: "server_vad",
                threshold: 0.5,
                prefix_padding_ms: 300,
                silence_duration_ms: 200,
    
            }
        }
    };

    if (enableInputAudioTranscription) {
        command.session.input_audio_transcription = {
            model: "whisper-1"
        };
    }

    sendJsonMessage(command);
};


  const addUserAudio = (base64Audio: string) => {  
    const command: InputAudioBufferAppendCommand = {  
      type: "input_audio_buffer.append",  
      audio: base64Audio,  
    };  
    sendJsonMessage(command);  
  };  
  
  const inputAudioBufferClear = () => {  
    const command: InputAudioBufferClearCommand = {  
      type: "input_audio_buffer.clear",  
    };  
    sendJsonMessage(command);  
  };  
  
  const onMessageReceived = (event: MessageEvent) => {  
    onWebSocketMessage?.(event);  
  
    let message: Message;  
    try {  
      message = JSON.parse(event.data);  
    } catch (e) {  
      console.error("Failed to parse JSON message:", e);  
      return;  
    }  
  
    switch (message.type) {  
      case "session.waiting":  
        if (isSessionWaitingMessage(message)) {  
          onSessionWaiting?.(message);  
        }  
        break;  
      case "session_ready":  
        if (isSessionReadyMessage(message)) {  
          onSessionReady?.(message.partner_lang);  
        }  
        break;  
      case "response.done":  
        onReceivedResponseDone?.(message as ResponseDone);  
        break;  
      case "response.audio.delta":  
        onReceivedResponseAudioDelta?.(message as ResponseAudioDelta);  
        break;  
      case "response.audio_transcript.delta":  
        onReceivedResponseAudioTranscriptDelta?.(message as ResponseAudioTranscriptDelta);  
        break;  
      case "input_audio_buffer.speech_started":  
        onReceivedInputAudioBufferSpeechStarted?.(message);  
        break;  
      case "conversation.item.input_audio_transcription.completed":  
        onReceivedInputAudioTranscriptionCompleted?.(message as ResponseInputAudioTranscriptionCompleted);  
        break;  
      case "extension.middle_tier_tool_response":  
        onReceivedExtensionMiddleTierToolResponse?.(message as ExtensionMiddleTierToolResponse);  
        break;  
      case "error":  
        onReceivedError?.(message);  
        break;  
      default:  
        console.warn("Unhandled message type:", message.type);  
    }  
  };  
  
  return { startSession, addUserAudio, inputAudioBufferClear };  
}  