import subprocess

def main():
    print("Installing docling-serve without dependencies...")
    subprocess.check_call([
        "uv", "pip", "install", "--no-deps", "docling-serve==1.16.1"
    ])