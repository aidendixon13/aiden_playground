import os


def main():
    env_mode = os.environ.get("ENV_MODE", "not set")
    print(f"ENV_MODE: {env_mode}")


if __name__ == "__main__":
    main()
