declare global {
    interface Window {
    __env?: {
    VITE_BACKEND_WS_URL: string;
    // add other runtime environment variables as needed.
    };
    }
    }
    
    export {};
    