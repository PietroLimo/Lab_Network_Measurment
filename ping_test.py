from pythonping import ping

response = ping("8.8.8.8", count=4)
print(response)