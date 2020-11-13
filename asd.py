import requests
a = None
file = open('/home/sergey/Desktop/some_vid.mp4', 'rb')
a = file.read()
file.close()    
files = {'file_in': ('some_name', a,
 'video/mp4')}

    # curl request
r = requests.put('http://localhost:5005/api/upload/613123fc9b3e430cbd46b0f53cf2774f',
    files=files)
    
# print(r.text)