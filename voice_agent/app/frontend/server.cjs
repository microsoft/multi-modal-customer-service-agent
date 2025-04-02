// server.cjs (using CommonJS syntax)  
const express = require("express");  
const path = require("path");  
const fs = require("fs");  
  
const app = express();  
const port = process.env.PORT || 3000;  
const backendWsUrl = process.env.VITE_BACKEND_WS_URL || "ws://localhost:8765";  
  
// Serve static files from the "dist" folder  
app.use(express.static(path.join(__dirname, "dist")));  
  
// For any route, read index.html and inject the runtime config before sending  
app.get("/*", (req, res) => {  
  const indexFilePath = path.join(__dirname, "dist", "index.html");  
  fs.readFile(indexFilePath, "utf8", (err, data) => {  
    if (err) {  
      console.error("Error reading index.html:", err);  
      return res.status(500).send("Server Error");  
    }  
    // Inject inline script to set window.__env  
    const injectedData = data.replace(  
      "<head>",  
      `<head><script> window.__env = { VITE_BACKEND_WS_URL: "${backendWsUrl}" }; </script>`  
    );  
    res.send(injectedData);  
  });  
});  
  
// Start the server  
app.listen(port, () => {  
  console.log(`Server running on port ${port}`);  
});  