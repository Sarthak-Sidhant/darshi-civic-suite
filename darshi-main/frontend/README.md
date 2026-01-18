# Darshi Frontend - SvelteKit

Modern, lightweight frontend for the Darshi civic grievance platform built with SvelteKit 5.

## Features

- Report submission with image upload and location services
- Real-time report listing with filtering
- Detailed report views with comments and upvoting
- Admin dashboard for report management
- User authentication (login/register)
- Responsive design for mobile and desktop
- Hotspot alerts for critical areas

## Tech Stack

- SvelteKit 5 (with Runes)
- TypeScript
- Native CSS (no frameworks - ultra lightweight)
- Vite

## Development

### Prerequisites

- Node.js 18+ and npm
- Backend API running on http://localhost:8080

### Setup

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env

# Edit .env to configure API URL if needed
# VITE_API_URL=http://localhost:8080/api/v1

# Start development server
npm run dev

# Or open in browser automatically
npm run dev -- --open
```

The app will be available at http://localhost:5173

### Building for Production

```bash
# Build the app
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── lib/
│   ├── api.ts          # API client functions
│   └── stores.ts       # Svelte stores for state management
├── routes/
│   ├── +layout.svelte  # Main layout with navigation
│   ├── +page.svelte    # Home page (reports listing)
│   ├── submit/         # Report submission page
│   ├── report/[id]/    # Individual report detail
│   ├── login/          # Login page
│   ├── register/       # Registration page
│   └── admin/          # Admin dashboard
```

## Environment Variables

- `VITE_API_URL` - Backend API base URL (default: http://localhost:8080/api/v1)

## Key Features

### Report Submission
- Multi-image upload support
- GPS location detection
- Address geocoding with search
- Form validation

### Report Viewing
- Grid layout with responsive design
- Status badges and severity indicators
- Upvoting system
- Comments section
- Timeline of report updates

### Admin Dashboard
- Overview statistics
- Report management table
- Status update modal
- Real-time updates

### Authentication
- JWT-based authentication
- Persistent login with localStorage
- Role-based access control
- Protected routes

## API Integration

All API calls are centralized in `src/lib/api.ts`. The frontend communicates with the FastAPI backend using:

- Form data for file uploads
- JSON for other requests
- Bearer token authentication for protected routes
- URL-encoded form data for OAuth2 login

## Performance

- No external CSS frameworks (pure CSS)
- Minimal JavaScript bundle
- Lazy loading of routes
- Optimized images
- Fast page transitions

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile browsers (iOS Safari, Chrome Mobile)
