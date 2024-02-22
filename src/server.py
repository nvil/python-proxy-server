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

connect_counter = 1

if sender == 0:
    listening_port = INTERNAL_PROXY_PORT #'55555'

def encrypt_str(data) -> bytearray:
    data = data[::-1]
    result = bytearray(data)
    for i in range(len(result)):
        result[i] = (result[i] + 2) & 0xff
    return result

def decrypt_str(data) -> bytearray:
    data = data[::-1]
    result = bytearray(data)
    for i in range(len(result)):
        result[i] = (result[i] - 2) & 0xff
    return result

def start():    #Main Program
    print('\n\n')
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

    # test code
    test_bytes = bytearray.fromhex('fffefdfc')
    print('\n')
    print(f'Test   : {test_bytes}')
    encrypt_bytes = encrypt_str(test_bytes)
    print(f'Encrypt: {encrypt_bytes}')
    decrypt_bytes = decrypt_str(encrypt_bytes)
    print(f'Decrypt: {decrypt_bytes}')
    if test_bytes == decrypt_bytes:
        print('[*] Encrypt Test Success!!')
    else:
        print('[*] Encrypt Test Failure!!')
    print('\n')

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
    global sender, connect_counter

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
            port = INTERNAL_PROXY_PORT
        else:
            webserver = 'localhost'
            port = 443

        print('\n-------------------------------')
        print(f'\n[*] New connection established... {connect_counter}\n')
        connect_counter += 1
        proxy_server(webserver, port, conn, addr, data)
    except Exception as e:
        print(e)
        traceback.print_exc()
        pass

def proxy_server(webserver, port, conn, addr, data):
    global sender, buffer_size

    try:
        reply = ''
        sock = 0
        socket_counter = 1
        while True:
            print('-------------------------------')
            if sender == 1:
                print(data)
                data = encrypt_str(data)
            else:
                data = decrypt_str(data)
                try:
                    print(data.decode())
                except UnicodeDecodeError:
                    print(data)
            print(f'\n---- Data length:{len(data)}\n')

            #Create a new socket if it is not created already. Else reuse the existing socket.
            if sock == 0:
                print('-------------------------------')
                print(f'[*] Creating a new socket... {socket_counter}')
                print()
                print(f'[*] Connect to {webserver}:{port}, {conn}, return addr:{addr}') #Debugging purpose 
                print('-------------------------------')
                print()
                socket_counter += 1
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((webserver, port))

            sock.send(data)

            try:
                reply = sock.recv(buffer_size)
                if len(reply) > 0:
                    if sender == 1:
                        reply = decrypt_str(reply)
                        try:
                            print(reply.decode())
                        except UnicodeDecodeError:
                            print(reply)
                    else:
                        print(reply)
                        reply = encrypt_str(reply)

                    print('-------------------------------')
                    conn.send(reply)
                    
                    dar = float(len(reply))
                    dar = float(dar/1024)
                    dar = f"{dar:.3f} KB"
                    print()
                    print(f"[*] Request Done: {addr[0]}:{addr[1]} => {dar} <=\n")

            except KeyboardInterrupt:
                print("\n[*] User has requested an interrupt")
                print("[*] Application Exiting.....")
                sock.close()
                conn.close()
                sys.exit(1)

            if len(reply) > 0:
                try:
                    data = conn.recv(buffer_size) #Recieve client data
                    if len(data) == 0:
                        print(f"[*] Connection Closed: {addr[0]}:{addr[1]}\n")
                        break # exit outer loop
                except Exception as e:
                    print(e)
                    data = ''
                    break # exit outer loop
            else:
                print(f"[*] Connection Closed: {addr[0]}:{addr[1]}\n")
                data = ''
                break # exit outer loop

            # end of outer while loop
            pass
        # outer while loop

        sock.close()
        conn.close()

    except socket.error:
        sock.close()
        conn.close()
        print(sock.error)
        sys.exit(1)

if __name__== "__main__":
    start()
