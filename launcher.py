import os, sys
from pathlib import Path
from time import sleep
import uvicorn
import socket
import webbrowser
import threading
from os.path import join, exists
from bomiot_token import encrypt_info
from os import getcwd
import tkinter as tk
from PIL import Image, ImageTk
import requests

app_name = "GreaterWMS"
version = "3.0.0"
port = 8008


def _port_available(p: int) -> bool:
    """Check if a TCP port is available for binding (no other process is listening on it)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', p))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _find_available_port(start_port: int, max_tries: int = 100) -> int:
    """Starting from start_port, return the first port that is not in use (increment by 1 each try)."""
    for candidate in range(start_port, start_port + max_tries):
        if _port_available(candidate):
            if candidate != start_port:
                print(f"Port {start_port} is in use, switched to port {candidate}")
            return candidate
    raise RuntimeError(f"No available port in range [{start_port}, {start_port + max_tries - 1}]")


if __name__ == "__main__":
    # Welcome page
    splash = tk.Tk()
    window_width = 675
    window_height = 329
    x = int(splash.winfo_screenwidth() / 2 - window_width / 2)
    y = int(splash.winfo_screenheight() / 2 - window_height / 2)
    canvas = tk.Canvas(splash, width=window_width, height=window_height, bg='white', highlightthickness=0)
    canvas.pack()

    splash.title("Welcome to Bomiot")
    splash.geometry(f'675x329+{x}+{y}')
    splash.overrideredirect(True)  # Borderless display
    # Load and scale image (maintain aspect ratio)
    try:
        # Load image using PIL
        image_path = join(getcwd(), 'splash.png')
        pil_img = Image.open(image_path)

        # Get original image dimensions
        img_width, img_height = pil_img.size

        # Calculate scale ratio (maintain aspect ratio)
        scale_width = window_width / img_width
        scale_height = window_height / img_height
        scale = min(scale_width, scale_height)  # Use minimum ratio to ensure image fits entirely within window

        # Calculate scaled dimensions
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)

        # Scale image
        resized_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)  # High quality scaling
        img = ImageTk.PhotoImage(resized_img)

        # Calculate center position for image
        x_pos = (window_width - new_width) // 2
        y_pos = (window_height - new_height) // 2

        # Display image on canvas (centered)
        canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=img)
    except Exception as e:
        print(f"Failed to load image: {e}")
        # Display error text
        canvas.create_text(window_width / 2, window_height / 2, text="Failed to load image", font=("Arial", 12))

    # Force window refresh to ensure splash is displayed before subsequent operations
    splash.update()
    # Set Django environment variables
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bomiot.server.server.settings")
    os.environ.setdefault("RUN_MAIN", "true")
    os.environ.setdefault("IS_LAN", "true")
    os.environ.setdefault('WORKERS', '1')
    lockfile = Path(join(os.path.dirname(sys.executable), 'bomiot_ready.lock'))
    if lockfile.exists():
        lockfile.unlink()
    import django

    django.setup()

    auth_key_path = Path(join(os.path.dirname(sys.executable), 'auth_key.py'))
    if auth_key_path.exists():
        auth_key_path.unlink()
    while True:
        community_key, sponsor_key = encrypt_info()
        if '/' in community_key or '/' in sponsor_key:
            continue
        else:
            break
    with open(auth_key_path, "w", encoding="utf-8") as f:
        f.write(f'COMMUNITY_KEY = "{community_key}"\n')
        f.write(f'SPONSOR_KEY = "{sponsor_key}"\n')

    from django.core.management import call_command
    from django.apps import apps
    from django.contrib.auth import get_user_model

    # Prepare makemigrations command arguments
    cmd_args = ["makemigrations"]

    # Auto-detect all apps with models
    apps_with_models = []
    for app_config in apps.get_app_configs():
        try:
            if app_config.models_module:
                models = apps.get_app_config(app_config.label).get_models()
                if models:
                    apps_with_models.append(app_config.label)
        except Exception:
            continue

    if apps_with_models:
        cmd_args.extend(apps_with_models)

    # Execute makemigrations command
    try:
        call_command(*cmd_args)
        print("Migrations created successfully.")
    except Exception as e:
        print(f"Error creating migrations: {e}")

    # Execute migrate command
    try:
        call_command('migrate')
    except Exception as e:
        print(f"Error during migration: {e}")

    for app_config in apps.get_app_configs():
        try:
            app_config.ready()
        except Exception:
            pass

    # Execute makemigrations command again
    try:
        call_command(*cmd_args)
        print("Migrations created successfully.")
    except Exception as e:
        print(f"Error creating migrations: {e}")

    # Execute migrate command again
    try:
        call_command('migrate')
    except Exception as e:
        print(f"Error during migration: {e}")

    # Keep welcome page displayed for a while (original logic: 10 seconds)
    print('System is starting up')

    # Start Django development server
    # ---- port auto-increment: if 8008 is taken, try 8009, 8010, ... up to 100 ports ----
    port = _find_available_port(port)

    print('System started successfully')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    print('Local IP address:', ip)
    s.close()
    baseurl = "http://" + ip + ":" + str(port)
    print('Opening browser at:', baseurl)


    def run_server():
        while True:
            try:
                response = requests.get(url=baseurl, timeout=2)
                print(response.status_code)
                sleep(2)
                webbrowser.open(baseurl)
                break
            except:
                print("Server not ready yet, retrying...")
                sleep(0.5)
                continue


    run_server_thread = threading.Thread(target=run_server, daemon=True)
    run_server_thread.start()

    # Manually destroy the welcome page before starting uvicorn
    splash.destroy()

    uvicorn.run(
        "bomiot_asgi:application",
        host='0.0.0.0',
        port=port,
        workers=1,
        log_level="info",
        uds=None,
        ssl_keyfile=None,
        ssl_certfile=None,
        proxy_headers=True,
        http="httptools",
        server_header=False,
        limit_concurrency=1000,
        backlog=128,
        timeout_keep_alive=5,
        timeout_graceful_shutdown=30,
        loop="auto",
    )


