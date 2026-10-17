import main


if __name__ == "__main__":
    main.mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
    )
