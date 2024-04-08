import requests
from mimetypes import guess_type
import os

class PeertubeChannel():
    def __init__(self, domain_url, channel_id=None, channel_name=None):
        if not channel_id:
            data = requests.get(f'{domain_url}/api/v1/video-channels/{channel_name}').json()
            channel_id = data["id"]
        self.domain_url = domain_url
        self.channel_name = channel_name
        self.id = channel_id

class PeertubeVideo():
    def __init__(self, video_id, domain_url, headers):
        self.headers = headers
        self.end_point = f'{domain_url}/api/v1/videos/{video_id}'
        self.video_id = video_id

    def get_properties(self):
        return requests.get(self.end_point, headers=self.headers).json()

    def set_property(self, property_name, value):
        #this hack used to fix pluginData properties, but it seems to have stopped working
        return requests.put(self.end_point, headers=self.headers, files={property_name: (None, value)})
    
class PeertubePlaylist():
    def __init__(self, domain_url, headers, playlist_id=None, playlist_name=None):
        self.headers = headers
        if playlist_id:
            self.end_point = f'{domain_url}/api/v1/video-playlists/{playlist_id}'
        elif playlist_name:
            response = requests.post(f'{domain_url}/api/v1/video-playlists', headers=self.headers, files={"displayName": (None, playlist_name)})
            print(response.json())
            playlist_id = response.json()["videoPlaylist"]["shortUUID"]
        self.playlist_id = playlist_id
        self.end_point = f'{domain_url}/api/v1/video-playlists/{playlist_id}'

    def add_video(self, video_id):
        response = requests.post(f'{self.end_point}/videos', headers=self.headers, data={"videoId": video_id})
        return response

class PeertubeUploader():
    def __init__(self, domain_url, username, password):
        self.api_url = domain_url + "/api/v1"
        oauth_data = requests.get(self.api_url + "/oauth-clients/local").json()
        #import ipdb; ipdb.set_trace()
        #print("rfrfefrerfwfwfrww")
        client_id = oauth_data["client_id"]
        client_secret = oauth_data["client_secret"]
        self.data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'password',
            'response_type': 'code',
            'username': username,
            'password': password
        }
        self.domain_url = domain_url

        token_data = requests.post(self.api_url + "/users/token", data=self.data).json()
        print(token_data)
        token_type = token_data["token_type"]
        access_token = token_data["access_token"]
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def upload_file(self, filepath, channel_id=2, title=None, tags=[], privacy=4, description=None):
        if not title:
            title = filepath
        def get_video_chunks(f, chunk_size):
            #with open(file_name, "rb") as f:
            while True: 
                data = f.read(chunk_size)
                if not data:
                    break
                yield data

        with open(filepath, "rb") as f:
            video_data = {"channelId": channel_id,
                "name": title,
                "filename": filepath,
                "privacy": privacy,
                "tags": tags
            }
            if description: video_data["description"] = description
            
            print(video_data)

            file_chunk_size = 262144
            chunks = get_video_chunks(f, file_chunk_size)
            file_size = os.stat(filepath).st_size

            resumable_headers = dict(self.headers)
            resumable_headers["X-Upload-Content-Length"] = str(file_size)
            resumable_headers["X-Upload-Content-Type"] = self.get_mimetype(filepath)

            response = requests.post(self.api_url + "/videos/upload-resumable",
                                    headers=resumable_headers,
                                    data=video_data
                                    ) 

            video_id_path = f'https:{response.headers["location"]}'

            byte_index = 0
            for c in chunks:
                while True:
                    chunk_headers = dict(self.headers)
                    chunk_headers["Content-Type"] = "application/octet-stream"
                    chunk_headers["Content-Length"] = str(len(c))
                    chunk_headers["Content-Range"] = f"bytes {byte_index}-{byte_index+(len(c)-1)}/{file_size}"
                    try:
                        rrr = requests.put(video_id_path, headers=chunk_headers, data=c)
                        progress = (100.0 / file_size) * byte_index
                        print(f"{rrr.status_code} {progress}%")
                        if rrr.status_code == 308:
                            byte_index += len(c)
                            break
                        elif rrr.status_code == 200:
                            video_id = rrr.json()["video"]["id"]
                            break
                        else:
                            import ipdb; ipdb.set_trace()
                    except:
                        print("error")

        return PeertubeVideo(video_id, self.domain_url, self.headers)
    
    def create_playlist(self, playlist_name):
        return PeertubePlaylist(self.domain_url, self.headers, playlist_name=playlist_name)    

    def get_mimetype(self, filepath):
        return guess_type(filepath)[0]
