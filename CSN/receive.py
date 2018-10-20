import socket

s = socket.socket()
host = '192.168.42.2'  # ip of host!
port = 12345
s.bind((host, port))

s.listen(5)
while True:
    c, addr = s.accept()
    print('Got connection from ' + str(addr))
    c.send(str.encode('Thank you for connecting'))
    c.close()
