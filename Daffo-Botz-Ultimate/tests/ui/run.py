import subprocess,time,urllib.request,sys
p=subprocess.Popen([sys.executable,'tests/ui/server.py'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:8765/healthz',timeout=.2);break
  except Exception:time.sleep(.05)
 else:raise RuntimeError('server did not start')
 r=subprocess.run(['node','tests/ui/check.mjs'])
 sys.exit(r.returncode)
finally:
 p.terminate()
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:p.kill()
 print(p.stdout.read().decode()[-1500:])
