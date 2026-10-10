import os
from dotenv import load_dotenv
load_dotenv()
os.umask(0o077)
from web.app import create_app
app=create_app()
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host=os.getenv('HOST','127.0.0.1'),port=int(os.getenv('PORT','8000')),workers=1,proxy_headers=False,access_log=False)
