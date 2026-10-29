"""Compare the actual HTTP Load route with direct address installation."""
import sys,os,http.client,threading
from pathlib import Path
from tempfile import TemporaryDirectory
from http.server import ThreadingHTTPServer
from unittest.mock import patch
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from ControllerUploader import install_controller,controller_files,SimpleHTTPRequestHandler
with TemporaryDirectory() as temp:
 root=Path(temp);browser=root/'browser/robot0Controller';direct=root/'direct/robot0Controller'
 browser.mkdir(parents=True);direct.mkdir(parents=True)
 class Handler(SimpleHTTPRequestHandler):
  def translate_path(self,path):return str(browser)
  def log_message(self,*args):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 checks=0
 try:
  for name in ('test.py','UPPER.PY','robot0Controller.PY','compiled','test.exe','test.class','test.jar','test.bsg','test.m'):
   for directory in (browser,direct):
    for p in directory.iterdir():p.unlink()
    (directory/'robot0Controller.py').write_bytes(b'previous Python')
    (directory/'robot0Controller.exe').write_bytes(b'previous executable')
    (directory/'helper.txt').write_bytes(b'keep this dependency')
   data=b'program bytes\x00\xff\r\nsecond line\nfinal bytes'
   boundary='SharedControllerLoadTest'
   body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file1"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()+data+f'\r\n--{boundary}--\r\n'.encode())
   connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
   connection.request('POST','/controllers/robot0Controller/',body,{'Content-Type':f'multipart/form-data; boundary={boundary}'})
   response=connection.getresponse();text=response.read();connection.close();assert response.status==200,(name,text)
   target=install_controller(name,data,direct)
   assert target.name=='robot0Controller'+Path(name).suffix.lower()
   assert controller_files(direct)==[target]
   a={p.name:p.read_bytes() for p in browser.iterdir()};b={p.name:p.read_bytes() for p in direct.iterdir()}
   assert a==b,(name,a.keys(),b.keys());assert a[target.name]==data
   assert a['helper.txt']==b'keep this dependency'
   if os.name != "nt":  # Windows does not expose POSIX execute permission bits.
    assert target.stat().st_mode & 0o111 == 0o111
   checks+=1
  before={p.name:p.read_bytes() for p in direct.iterdir()}
  for name in ('raw.c','raw.cpp','../bad.py'):
   try:install_controller(name,b'new',direct)
   except ValueError:pass
   else:raise AssertionError('Unsupported filename accepted')
   assert before=={p.name:p.read_bytes() for p in direct.iterdir()}
  # Empty input must never replace a working program, through either loading route.
  for name in ('empty.py','robot0Controller.m'):
   try:install_controller(name,b'',direct)
   except ValueError as error:assert 'empty' in str(error)
   else:raise AssertionError('Empty file accepted')
   assert before=={p.name:p.read_bytes() for p in direct.iterdir()}
  browser_before={p.name:p.read_bytes() for p in browser.iterdir()}
  boundary='EmptyUpload'
  body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file1"; filename="robot0Controller.m"\r\nContent-Type: application/octet-stream\r\n\r\n\r\n--{boundary}--\r\n').encode()
  connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
  connection.request('POST','/controllers/robot0Controller/',body,{'Content-Type':f'multipart/form-data; boundary={boundary}'})
  response=connection.getresponse();text=response.read();connection.close()
  assert response.status==500 and b'empty' in text
  assert browser_before=={p.name:p.read_bytes() for p in browser.iterdir()}
  with patch('ControllerUploader.os.replace',side_effect=OSError('test write failure')):
   try:install_controller('new.py',b'new',direct)
   except OSError:pass
   else:raise AssertionError('Write failure ignored')
  assert before=={p.name:p.read_bytes() for p in direct.iterdir()}
  # A path pointing at the installed program must not delete its own source.
  current=direct/'robot0Controller.m';payload=current.read_bytes()
  install_controller(current.name,payload,direct);assert current.read_bytes()==payload
 finally:server.shutdown();server.server_close();thread.join()
print(f'PASS: {checks} HTTP/address format parity cases; binary bytes, uppercase names, self-copy, old entrypoint replacement, dependencies, failed writes and unsupported types.')
