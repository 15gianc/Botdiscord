import os
from dotenv import load_dotenv

print("Directorio donde se ejecuta:", os.getcwd())
print("Archivos visibles:", os.listdir('.'))
print("Existe .env exactamente?:", os.path.exists('.env'))

load_dotenv()

print("\nVariables leídas:")
print("TOKEN:", os.getenv("TOKEN"))
print("TWITCH_USERNAME:", os.getenv("TWITCH_USERNAME"))
print("DISCORD_NOTIFY_CHANNEL_ID:", os.getenv("DISCORD_NOTIFY_CHANNEL_ID"))