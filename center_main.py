import uvicorn


def main():
    print("Starting CQUPT Rollcall Center Server...")
    uvicorn.run("center_server.center_server:app", host="0.0.0.0", port=8081)


if __name__ == "__main__":
    main()
