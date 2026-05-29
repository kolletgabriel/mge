import os

import uvicorn


uvicorn.run('back:app',
    uds = os.environ['UVICORN_UDS'],
    forwarded_allow_ips = os.environ['UVICORN_UDS']
)
