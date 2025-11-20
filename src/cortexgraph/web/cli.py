import uvicorn


def main():
    """Run the web server."""
    # config = get_config()
    # Use default host/port or make configurable
    uvicorn.run("cortexgraph.web.app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
