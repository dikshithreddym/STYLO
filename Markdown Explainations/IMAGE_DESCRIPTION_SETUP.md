# Image Description Feature - Setup Guide

This feature automatically generates AI-powered descriptions for wardrobe items when they are uploaded.

## How It Works

1. **Upload**: User uploads a clothing item image via the "Add Item" modal
2. **Analysis**: The backend sends the image to Google Gemini API for analysis
3. **Storage**: The AI-generated description is stored in the database
4. **Display**: When viewing an item, the description appears in a blue info box

## Setup Instructions

### 1. Run Database Migration

First, add the new `image_description` column to your database:

```bash
cd backend
python migrate_add_image_description.py
```

### 2. Configure Google Gemini API (Optional but Recommended)

To enable AI-powered image descriptions, add your Gemini API key to your `.env` file:

```bash
# backend/.env
GEMINI_API_KEY=your-api-key-here
```

**Get an API key from:** https://aistudio.google.com/app/apikey

**Note:** If you don't configure a Gemini API key, the system will automatically generate basic fallback descriptions based on the item type, color, and category.

### 3. Install Updated Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This adds the `requests` library needed for API calls.

### 4. Restart Your Backend Server

```bash
cd backend
uvicorn app.main:app --reload
```

### 5. Test the Feature

1. Go to your wardrobe page
2. Click "Add Item"
3. Upload an image of clothing
4. Fill in the details and save
5. Click "View" on the newly added item
6. You should see a description box with AI-generated text

## Cost Considerations

- **Model Used**: `gemini-1.5-flash` (cost-efficient vision model)
- **Cost**: Free tier available (15 requests/minute, 1500 requests/day)
- **Pricing**: Very affordable for production use (see Google AI pricing)

## Fallback Behavior

If OpenAI API is not configured or fails, the system automatically generates descriptions like:

- "A blue shirt that pairs well with various bottoms."
- "Versatile black jeans suitable for different occasions."
- "Comfortable white sneakers to complete your outfit."

## Environment Variables Summary

```bash
# Required for deployment
DATABASE_URL=postgresql://user:pass@host/db
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Optional - enables AI descriptions
GEMINI_API_KEY=your-gemini-api-key

# Optional settings
USE_CLOUDINARY=true
CLOUDINARY_FOLDER=stylo_wardrobe
MAX_IMAGE_SIZE=10485760
FRONTEND_URL=http://localhost:3000
```

## Deployment Notes

When deploying to Render or other platforms:

1. Add `GEMINI_API_KEY` to environment variables in the dashboard
2. The migration will run automatically on first deployment if using the build script
3. Ensure `requests` is in `requirements.txt` (already added)

## API Response Structure

The `/wardrobe` endpoint now includes `image_description`:

```json
{
  "id": 1,
  "type": "Hoodie",
  "color": "black",
  "image_url": "https://cloudinary.com/...",
  "category": "layer",
  "image_description": "A comfortable black hoodie with a zippered front and hood, perfect for casual wear or layering in cooler weather."
}
```

## Troubleshooting

### "Column image_description does not exist"
Run the migration script: `python migrate_add_image_description.py`

### "No descriptions appearing"
Check if `GEMINI_API_KEY` is set. If not, fallback descriptions should still appear.

### "Gemini API error"
- Verify your API key is valid at https://aistudio.google.com/app/apikey
- Check you haven't exceeded the free tier limits (15 req/min, 1500 req/day)
- Review backend logs for detailed error messages

### "Image upload works but no description"
- Check backend logs for errors
- Verify the image is in base64 format or valid URL
- Ensure `requests` library is installed
