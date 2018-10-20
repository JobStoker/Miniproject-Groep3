import socket

s = socket.socket()
host = '192.168.42.2'  # ip of host!
port = 12345
s.connect((host, port))

print(s.recv(1024))
s.close()
