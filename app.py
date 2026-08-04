from weather_agent.ui import APP_CSS, APP_THEME, build_app


demo = build_app()


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=4).launch(
        server_name="0.0.0.0",
        server_port=7860,
        theme=APP_THEME,
        css=APP_CSS,
    )
