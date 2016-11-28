import socket
import ipaddress


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = socket.gethostname()
host = '169.254.108.151'
print host
port = 12345
s.bind((host, port))

s.listen(5)
while True:
  c, addr = s.accept()
  print ('Got connection from',addr)
  c.send('Thank you for connecting')
  c.close()