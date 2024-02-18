import argparse
import socket
import sys
import traceback
from _thread import *

from decouple import config

INTERNAL_PROXY_PORT = 5555

try:
    listening_port = config('PORT', cast=int)
except KeyboardInterrupt:
    print("\n[*] User has requested an interrupt")
    print("[*] Application Exiting.....")
    sys.exit()

parser = argparse.ArgumentParser()

parser.add_argument('--max_conn', help="Maximum allowed connections", default=5, type=int)
parser.add_argument('--buffer_size', help="Number of samples to be used", default=8192, type=int)
parser.add_argument('--sender', help="Sender proxy for encrytion", default=1, type=int)

args = parser.parse_args()
max_connection = args.max_conn
buffer_size = args.buffer_size
sender = args.sender

if sender == 0:
    listening_port = INTERNAL_PROXY_PORT #'55555'

def encrypt_str(data) -> str:
    data = data[::-1]
    result = bytearray(data)
    for i in range(len(result)):
        result[i] = result[i] + 2
    return result

def decrypt_str(data) -> str:
    data = data[::-1]
    result = bytearray(data)
    for i in range(len(result)):
        result[i] = result[i] - 2
    return result

def start():    #Main Program
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind(('', listening_port))
        sock.listen(max_connection)
        if sender == 1:
            print("[*] 1. Sender Proxy Server started successfully [ %d ]" %(listening_port))
        else:
            print("[*] 2. Receiver Proxy Server started successfully [ %d ]" %(listening_port))

    except Exception as e:
        print("[*] Unable to Initialize Socket")
        print(e)
        sys.exit(2)

    while True:
        try:
            conn, addr = sock.accept() #Accept connection from client browser
            data = conn.recv(buffer_size) #Recieve client data
            start_new_thread(conn_string, (conn,data, addr)) #Starting a thread
        except KeyboardInterrupt:
            sock.close()
            print("\n[*] Graceful Shutdown")
            sys.exit(1)

def conn_string(conn, data, addr):
    try:
        #print(data)
        first_line = data.split(b'\n')[0]

        url = first_line.split()[1]

        http_pos = url.find(b'://') #Finding the position of ://
        if(http_pos == -1):
            temp=url
        else:
            temp = url[(http_pos+3):]
        
        port_pos = temp.find(b':')

        webserver_pos = temp.find(b'/')
        if webserver_pos == -1:
            webserver_pos = len(temp)
        webserver = ""
        port = -1
        if(port_pos == -1 or webserver_pos < port_pos):
            port = 80
            webserver = temp[:webserver_pos]
        else:
            port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
            webserver = temp[:port_pos]
        #print(data)
        if sender == 1:
            webserver = 'localhost'
            #webserver = '59.11.41.207'
            port = INTERNAL_PROXY_PORT
        else:
            webserver = 'localhost'
            port = 443
        proxy_server(webserver, port, conn, addr, data)
    except Exception as e:
        print(e)
        traceback.print_exc()
        pass

def proxy_server(webserver, port, conn, addr, data):
    try:
        if sender == 1:
            data = encrypt_str(data)
        else:
            data = decrypt_str(data)

        print('-------------------------------')
        print(data)
        print('-------------------------------')
        print(webserver, port, conn, addr) #Debugging purpose 
        print('-------------------------------')
        print()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((webserver, port))
        sock.send(data)

        while 1:
            reply = sock.recv(buffer_size)
            if(len(reply)>0):
                if sender == 1:
                    reply = decrypt_str(reply)
                else:
                    reply = encrypt_str(reply)

                conn.send(reply)
                
                dar = float(len(reply))
                dar = float(dar/1024)
                dar = "%.3s" % (str(dar))
                dar = "%s KB" % (dar)
                print("[*] Request Done: %s => %s <=" % (str(addr[0]), str(dar)))

            else:
                break

        sock.close()

        conn.close()
    except socket.error:
        sock.close()
        conn.close()
        print(sock.error)
        sys.exit(1)



if __name__== "__main__":
    start()
