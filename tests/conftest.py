import os

# CI runners may set HTTP(S)_PROXY; every test talks to 127.0.0.1.
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
