#!/bin/bash

  nPrj=3
  nStg=3
  bSwapPorts=1                                                      # .(60602.03.1
  nPort="${nPrj}${nStg}##"
  aQuiet=""; if [ "$2" == "-q" ]; then aQuiet="--quiet"; set -- "$1" "${@:3}"; fi
             if [ "$3" == "-q" ]; then aQuiet="--quiet"; fi

# Function to kill process on a specific port
function chkPort() {
    local port=$1; local pid
    echo -e "\n  Checking port $port..."

    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows (Git Bash)
               pid=$(netstat -ano | findstr ":$port" | awk '{print $5}' | head -1)
        if [ "$pid" != "0" ] && [ ! -z "$pid" ]; then
            echo "  Killing windows process $pid for port $port"
#           taskkill /PID $pid /F > /dev/null 2>&1
            MSYS2_ARG_CONV_EXCL="/PID;/F" /c/Windows/System32/taskkill.exe /PID "$pid" /F | awk '{ print "  " $0 }'
        fi
    else
        # Linux/macOS
               pid=$(lsof -ti:"$port")
        if [ "$pid" != "0" ] && [ ! -z "$pid" ]; then
            echo "  Killing linux process $pid for port $port"
            kill -9 "$pid" > /dev/null 2>&1
        fi
    fi
}
# ---------------------------------------------------

function setPort() { # $1 = 3201, 3251 or 64361: Proj#: 3,64; Stage#: 1)Prod, 2)Test, 3)Dev3, 4-9)Dev4-9; Client#/Server#: 0-4/5-9; App#: 1-9
    csn=${1:1:1}     # Client#/Server#
    ano=${1:2:1}     # App#
    pno="${2:0:2}"; if [ "${#2}" == "5" ]; then pno="${2:0:3}"; fi  # Proj#
 if [ "${bSwapPorts}" == "1" ]; then                         # .(60602.03.1 RAM Support both Beg)
    nsp=0;       if [ "${1:0:1}" == "c" ]; then nsp=5; fi    # .(60521.01.1 RAM Chg: server port 0x, client port 5x )
  else 
    nsp=5;       if [ "${1:0:1}" == "c" ]; then nsp=0; fi    # .(60521.01.1 RAM Was: server port 5x, client port 0x 
    fi                                                       # .(60602.03.1 End)
    nPort="${pno}$(( nsp + csn ))${ano}";
    aApp="${1:0:1}${csn}${ano}"
    aServer="server${csn}"; if [ "${csn}" == "0" ]; then aServer="server"; fi
    aClient="client${csn}"; if [ "${csn}" == "0" ]; then aClient="client"; fi
#   echo "--nPort: ${nPort}"
    }
# ---------------------------------------------------

function getAppName() {
   aAppName="Unknown"; setPort "$1" "$2"; aFldr="docs"
if [ "${1:0:1}" == "c" ]; then aFldr="${aClient}"; fi
if [ "${1:0:1}" == "s" ]; then aFldr="${aServer}"; fi
if [ -d "${aFldr}" ]; then
#  echo "-- \$( find "./${aFldr}" -maxdepth 1 -type d -name "${aApp}_*"                  | awk '{ sub( /.+\//, \"\" ); print; exit }' )"
#  aAppName=$(  find "./${aFldr}" -maxdepth 1 -type d -name "${aApp}_*" > /dev/null 2>&1 | awk '{ sub( /.+\//, ""   ); print; exit }' )
   aAppName=$(  find "./${aFldr}" -maxdepth 1 -type d -name "${aApp}_*"                  | awk '{ sub( /.+\//, ""   ); print; exit }' )
   fi
#  echo "-- aAppName: ${aAppName}"
   }
# ---------------------------------------------------

function runServer() {
    setPort "$1" "$2"      # Sets aServer, aApp and nPort
    chkPort "${nPort}"     # Kill any existing processes on our ports
    getAppName "$1" "$2";  # echo "--nPort: ${nPort} for ${aAppName}"; exit

#   Install dependencies if needed
    bDoit="0"; if [ "${3:0:2}" == "-d" ]; then bDoit="1"; fi
 if [ ! -d "${aServer}/node_modules"   ]; then bDoit="1"; fi
 if [ "${bDoit}" == "1" ] && [ -f "${aServer}/package.json" ]; then

    echo -e "\n  Installing ${aServer} dependencies..."
    cd "${aServer}" || return
    npm install
    cd ..
    fi
 if [ "$(command -v nodemon)" == "" ]; then npm install -g nodemon >/dev/null 2>&1; fi

 if [ ! -d "${aServer}/${aAppName}" ]; then                                                       #.(60525.01.1 RAM Check if folder exists Beg)
    echo -e "\n* WARNING: Server folder not found: ${aServer}/${aAppName}"
    return
    fi                                                                                            #.(60525.01.1 End)

    echo -e "\n  Starting server, ${aAppName}, on port ${nPort} ..."
#   cd ${aServer}/${aApp}_*
    cd "${aServer}/${aAppName}" || return 

    aVerbose=""; if [ "${aQuiet}" != "--quiet" ]; then aVerbose="-V"; fi                               # .(60602.01.1 RAM For nodemon) 
    aServerApp="s${aApp:1}_server.mjs"; if [ ! -f "${aServerApp}" ]; then aServerApp="server.mjs"; fi  # .(60531.01.1 RAM Check if running s01_server.mjs)

#   echo -e "\n  nodemon  --trace-deprecation  ${aVerbose} \"${aServer}/${aAppName}/${aServerApp}\" -- \"${nPort}\""
    nodemon --trace-deprecation  "${aVerbose}"  --watch ".,../../${aServer}/${aAppName}" "${aServerApp}" -- "${nPort}" &  # .(60531.01.2).(60531.02.1 RAM use nodemon and add nPort)

    SERVER_PID=$!
    echo "  Server is running at: http://localhost:${nPort}/api"
#   if [ "${aQuiet}"   == "" ]; then echo ""; fi
    echo "" 
    cd ../..
    }
# ---------------------------------------------------

function runClient() {
    setPort "$1" "$2"      # Sets aClient, aApp and nPort
    chkPort "${nPort}"     # Kill any existing processes on our ports
    getAppName "$1" "$2";  # echo "--nPort: ${nPort} for ${aAppName}"; exit

#   Install dependencies if needed
    bDoit="0"; if [ "${3:0:2}" == "-d" ]; then bDoit="1"; fi
 if [ ! -d "${aClient}/node_modules"   ]; then bDoit="1"; fi
 if [ "${bDoit}" == "1" ] && [ -f "${aClient}/package.json" ]; then

    echo -e "\n  Installing ${aClient} dependencies..."
    cd "${aClient}" || return
    npm install
    cd ..
    fi

 if [ "$(command -v live-server)" == "" ]; then npm install -g live-server >/dev/null 2>&1; fi

 if [ ! -d "${aClient}/${aAppName}" ]; then                                                       #.(60525.01.2 RAM Check if folder exists Beg)
    echo -e "\n* WARNING: Client folder not found: ${aClient}/${aAppName}"
    return
    fi                                                                                            #.(60525.01.2 End)

    echo -e "\n  Starting client, ${aAppName}, on port ${nPort} ..."
#   cd ${aClient}/${aApp}_*
    cd "${aClient}/${aAppName}" || return

    aVerbose=""; if [ "${aQuiet}" != "--quiet" ]; then aVerbose="-V"; fi                               # .(60602.01.1 RAM For nodemon) 
    aClientApp="c${aApp:1}_index.html"; if [ ! -f "${aClientApp}" ]; then aClientApp="index.html"; fi  # .(60531.01.3)
    aClientApp="c${aApp:1}_runner.mjs"                                                                 # .(60603.04.1)

#   python -m SimpleHTTPServer
#   npx http-server@latest -p ${nPort} -s &
#   npx -q serve -p ${nPort} -s &
#   live-server                   ${aQuiet}                        --port="${nPort}" --watch=".,../../${aClient}/${aAppName}" &
#   live-server                   ${aQuiet} --open="${aClientApp}" --port="${nPort}" --watch=".,../../${aClient}/${aAppName}" &  ##.(60531.02.4 RAM Did watch aServer).(60602.01.1) 

#  echo -e "\n  nodemon  --trace-deprecation  ${aVerbose} \"${aClient}/${aAppName}/${aClientApp}\" -- \"${nPort}\""
    nodemon  --trace-deprecation  ${aVerbose} --watch ".,../../${aClient}/${aAppName}" "${aClientApp}" -- "${nPort}" &  # .(60602.01.1 RAM Use nodemon)
 if [ "$?" != "0" ]; then 
    echo -e "\n  Error:  nodemon  --trace-deprecation  ${aVerbose} \"${aClientApp}\" \"${nPort}\""
    exit
    fi 
    CLIENT_PID=$!
    echo "  Client is running at: http://localhost:${nPort}"
    cd ../..
    }
# -------------------------------------------------

    getAppName "s${1:1:2}" ${nPort}; # aServerName=${aAppName}
#   echo "  Starting ${aAppName}"; # exit

 if [ "${1:0:1}" == "s" ] || [ "${1:0:1}" == "a" ]; then
    runServer "s${1:1:2}" "${nPort}" "$2"
    sleep 6  # Wait for server to start
    fi
 if [ "${1:0:1}" == "c" ] || [ "${1:0:1}" == "a" ]; then
    runClient "c${1:1:2}" "${nPort}" "$2"
    fi
# ---------------------------------------------------

    echo -e "\n  Press Ctrl+C to stop one or both services\n"

#   Wait for user interrupt
#   trap "kill $SERVER_PID $CLIENT_PID; exit" INT
    trap 'kill $SERVER_PID $CLIENT_PID; exit' INT
    wait