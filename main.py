from app.main import app, config, logger


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting PersonalityAI server...")
    logger.info(f"Server configuration: {config.server.host}:{config.server.port}")
    logger.info(f"Debug mode: {config.server.debug}")
    logger.info(f"Cache directory: {config.cache.cache_dir}")

    if config.server.debug and config.is_development:
        uvicorn.run(
            "app.main:app",
            host=config.server.host,
            port=config.server.port,
            log_level="debug",
            reload=True,
        )
    else:
        uvicorn.run(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level="info",
            reload=False,
        )
