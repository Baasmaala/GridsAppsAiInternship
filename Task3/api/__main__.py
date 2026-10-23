import os

import uvicorn

from .app import create_app

HOST = "127.0.0.1"  # local only, on purpose. not a setting.


def main():
    port = int(os.environ.get("MASAR_PORT", "8001"))
    print(f"Masar API on http://{HOST}:{port}  (docs: http://{HOST}:{port}/docs)")
    uvicorn.run(create_app(), host=HOST, port=port)


if __name__ == "__main__":
    main()
