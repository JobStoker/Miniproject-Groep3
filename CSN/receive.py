import socket

s = socket.socket()
# host = '192.168.42.1'  # ip of host!
host = '127.0.0.1'
port = 12345
s.bind((host, port))

s.listen(5)
while True:
    c, addr = s.accept()
    print('Got connection from ' + str(addr))
    c.send(str.encode('Thank you for connecting'))
    c.close()
