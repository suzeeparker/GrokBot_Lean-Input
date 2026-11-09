
# formR Project: SCN3-Apps
Created on Fri May 29 2026 at 09:27:03
Created by root
Version 1.02

## Description
This starter app uses the formR folder structure.  It is opinionated with
a clear seperation of client versus server code.
- If you start with a single `index.html` file, put it in a client folder.
- If you start with a single `indexjs` express app, put it in a server folder.

## Folder Structure
```
  Folder Size     Files   Dirs  /C/Home/Shared/Repos/Project_/stage-author/. (3 levels)
+-------------- +------ +----- +----------------------------+-------------------+---------- +-------------+
         32,714       9     11  ./
         30,862      39     27  ./.git/
            594       1      0  ./.vscode/
              3       2      2  ./client/
              3       2      1  ./client/c01_client-first-app/
              0       0      0  ./data/
            688       3      1  ./docs/
              0       0      0  ./docs/a00_AI-App-Specs/
              2       1      2  ./server/
              2       1      1  ./server/s01_server-first-api/
              0       0      0  ./sources/
```
## Folder Descriptions
- **client**  - Frontend application(s)
- **server**  - Backend API(s) and services
- **data**    - Structured data files (JSON or DB)
- **docs**    - Project documentation
- **sources** - Unstructured files to process
- .vscode - Editor settings
- .git    - Git repository data

## Lean Input
The first Lean Input tool is `scraper-viewer`. Repository source is under `+skills/` and `+docs/b11_Scraper-Viewer/`. Installed skill names do not use the `b##` prefix. Commit subjects and folder rules are in `CONTRIBUTING.md`. The starter client and server trees are separate from that slice.

