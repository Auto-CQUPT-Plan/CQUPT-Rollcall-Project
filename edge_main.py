import uvicorn
from edge_server.config import config


def main():
    print("Starting CQUPT Rollcall Edge Server...")
    uvicorn.run("edge_server.edge_server:app", host="0.0.0.0", port=config.http_port)


if __name__ == "__main__":
    main()
