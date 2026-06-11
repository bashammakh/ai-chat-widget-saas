# --- Nginx image: reverse proxy for FastAPI + static hosting for widget.js ---
# Build context is the repository root so we can copy both the nginx config and
# the widget assets into a single image.
FROM nginx:1.27-alpine

# Reverse-proxy + static config.
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Static widget assets served from the document root.
COPY frontend-widget/ /usr/share/nginx/html/

EXPOSE 80 443
