# Simple Client/Server Application Specifications

## A. Data Structure
Location: `./data/documents.json`

Document Record Schema:
```json
{
  "id": "string (UUID)",
  "title": "string",
  "type": "string (pdf, txt, doc)",
  "filepath": "string (relative path to file in sources folder)",
  "dateUploaded": "string (ISO date)",
  "lastModified": "string (ISO date)"
}
```

## B. Server Structure
Location: `./server/s01_docs-viewer-api/`

### Setup and Running

1. Installation:
Note: Run the `npm install` command in the server folder, not in each app folder  
   ```bash
   if [ ! -d server/s01_docs-viewer-api ]; then mkdir -p server/s01_docs-viewer-api; fi 
   cd server
   npm init -y
   npm install express cors multer@2 uuid
   ```
2. Running the server:
   ```bash
   cd server/s01_docs-viewer-api
   node server.mjs
   ```
3. Testing endpoints:
   - Use curl or Postman
   - Base URL: http://localhost:3251/api/docs
   - Example: GET http://localhost:3251/api/docs (lists all documents)

### Server Files

1. **File: server.mjs**
- Initialize Express application
- Configure middleware (cors, json parser, multer)
- Import and use document routes
- Set server port and start listener
- Basic error handling

2. **File: routes.mjs**
API Endpoints:
- GET  /api/docs       - List all documents
- GET  /api/docs/:id   - Get specific document
- POST /api/docs       - Upload new document
- PUT  /api/docs/:id   - Update document
- DELETE /api/docs/:id - Delete document

Error Handling:
- 404 for document not found
- 400 for invalid requests
- 500 for server errors

File Storage:
- Physical files stored in `./sources` directory
- Filenames preserved with UUID prefix to prevent conflicts
- File paths stored in documents.json relative to sources folder








## C. Client Interface
Location: `./client/c01_docs-viewer-app/`
API_BASE: `http://localhost:3251/api/docs`

### Setup and Running

1. Installation:
Note: Run the `npm install` command in the server folder, not in each app folder  
   ```bash
   if [ ! -d client/c01_docs-viewer-api ]; then mkdir -p client/c01_docs-viewer-api; fi 

   ```
2. Running the client:
- Using Node HTTP Server:
   ```bash
   cd client/c02_docs-viewer-app
   npm install -g http-server
   http-server -p 3201   
   ```
   Then visit: http://localhost:3201

- Using VS Code Live Server:
   - Right-click on index.html
   - Select "Open with Live Server"
   - Browser will open automatically

### Files

1. **File: index.html** - Main HTML interface
2. **File: index.js**   - Client-side JavaScript logic


### Wire Diagram

```ascii
+----------------------------------------+
|          Document Manager 1            |
+----------------------------------------+
| Upload Document:                       |
| [Choose File]  [Upload Button]         |
+----------------------------------------+
| Select Document:                       |
| [Dropdown Menu▼]                       |
+----------------------------------------+
| Document Info:                         |
| +-----------------------------------+  |
| |  Title: sample.pdf                |  |
| |  Path: ./sources/4f5cab72d0s45... |  |
| |  Updated: 2024-01-15 08:20p       |  |
| |  Type: pdf                        |  |
| |  <br>                             |  |
| +-----------------------------------+  |
+----------------------------------------+
|    [Download] [Delete]                 |
+----------------------------------------+
```

### Interface Elements:
1. File Upload Section
   - File input field
   - Upload button (Green)
   - Progress indicator (optional)

2. Document Selection
   - Dropdown populated with available documents
   - Auto-refresh after operations

3. Document Information Display
   - Show document metadata
   - Display file path
   - Last modified date
   - File type

4. Action Buttons
   - Download button to retrieve file (Green)
   - Delete button with confirmation dialog (Red)

## D. Running app client and server:
Location: `./{Project Root Folder}`
Runs the server first, then the client 
```bash
   bash run-app.sh a01
```
