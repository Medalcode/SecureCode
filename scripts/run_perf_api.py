import uvicorn
from unittest.mock import patch
import urllib.request

original_urlopen = urllib.request.urlopen

def mock_urlopen(request, *args, **kwargs):
    if isinstance(request, urllib.request.Request):
        url = request.full_url
        if url.startswith("https://api.github.com"):
            new_url = url.replace("https://api.github.com", "http://127.0.0.1:8001")
            new_req = urllib.request.Request(
                new_url, 
                data=request.data, 
                headers=request.headers, 
                method=request.get_method()
            )
            return original_urlopen(new_req, *args, **kwargs)
    elif isinstance(request, str):
        if request.startswith("https://api.github.com"):
            request = request.replace("https://api.github.com", "http://127.0.0.1:8001")
    return original_urlopen(request, *args, **kwargs)

patcher = patch('urllib.request.urlopen', side_effect=mock_urlopen)
patcher.start()

if __name__ == "__main__":
    uvicorn.run("securecode.api.app:app", host="127.0.0.1", port=8000)
