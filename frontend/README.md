# STYLO Frontend

Next.js frontend application for STYLO wardrobe management.

## Setup Instructions

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create environment file:
```bash
cp .env.example .env.local
```

4. Update `.env.local` if needed (default API URL is http://localhost:8000)

## Running the Application

Start the development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

## Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with Navbar
│   │   ├── page.tsx            # Landing page
│   │   ├── dashboard/
│   │   │   └── page.tsx        # Dashboard page
│   │   └── wardrobe/
│   │       └── page.tsx        # Wardrobe page (fetches from API)
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Button.tsx      # Reusable button component
│   │   │   ├── Card.tsx        # Reusable card component
│   │   │   └── Input.tsx       # Reusable input component
│   │   └── layout/
│   │       └── Navbar.tsx      # Navigation component
│   └── lib/
│       ├── apiClient.ts        # Axios client configuration
│       └── api.ts              # API endpoints wrapper
├── public/                     # Static files
├── package.json
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
└── README.md
```

## Features

- ✅ Landing page with hero section and features
- ✅ Dashboard with stats overview
- ✅ Wardrobe page with API integration
- ✅ Responsive design with Tailwind CSS
- ✅ Type-safe with TypeScript
- ✅ Reusable UI components
- ✅ Clean architecture

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **HTTP Client:** Axios
- **Images:** Next.js Image component

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## Environment Variables

- `NEXT_PUBLIC_API_URL` - Backend API URL (default: http://localhost:8000)

## Notes

- Make sure the backend API is running before accessing the wardrobe page
- No authentication implemented yet (Phase 1)
- All data is currently dummy data from the backend
