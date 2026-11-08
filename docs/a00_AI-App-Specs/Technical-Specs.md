# Sample formR Client/Server Application Specifications

## A. Data Structure
Location: `./data`

## B. Server Structure
Location: `./server/c00_sample-client-app/`

### Setup and Running
1. Installation:
Note: Run the `npm install` command in the server folder, not in each app folder  
   ```bash
   cd server
   npm init -y
   npm install express cors 
   ```
2. Running the server:
   ```bash
   cd server/s00_sample-server-api
   node server.mjs
   ```
3. Testing endpoints:
   - Base URL: http://localhost:3250/api

### 1. server.mjs
- Initialize Express application
- Send static HTML: "<h3>from the formR Server at localhost:3250/api</h3>"  
- Set server port and start listener

## C. Client Interface
Location: `./client/c00_sample-client-app/`
API_BASE: `http://localhost:3250/api`

### Files
1. `index.html` - Main HTML interface

### Wire Diagram
```ascii
+----------------------------------------+
|    Welcome to then formR Client App    |
|       from the formR Server API        |   
+----------------------------------------+
```

### Loading the Client
1. Using Node HTTP Server:
   ```bash
   cd client/c00_sample-client-app
   npm install -g http-server
   http-server -p 3200 -s > /dev/null 2>&1
   ```
   Then visit: http://localhost:3200

2. Using VS Code Live Server:
   - Right-click on index.html
   - Select "Open with Live Server"
   - Browser will open automatically

## D. Running app client and server:
Location: `./{Project Root Folder}`
Runs the server first, then the client 
```bash
   bash run-app.sh a00
```

