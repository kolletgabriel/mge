from os import environ

import uvicorn


uvicorn.run('back:app', uds=environ['UVICORN_UDS'], forwarded_allow_ips='*')
