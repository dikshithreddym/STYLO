import cloudinary
import cloudinary.uploader
from app.config import settings

print(f"Cloud Name: {settings.CLOUDINARY_CLOUD_NAME}")
print(f"API Key: {settings.CLOUDINARY_API_KEY}")
print(f"Configured: {settings.cloudinary_configured}")

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

demo_url = "https://res.cloudinary.com/demo/image/upload/getting-started/shoes.jpg"
result = cloudinary.uploader.upload(demo_url, public_id="stylo_test_upload")

print(f"\nUpload Success!")
print(f"URL: {result['secure_url']}")
print(f"Public ID: {result['public_id']}")
print(f"Width: {result['width']} x {result['height']}")
