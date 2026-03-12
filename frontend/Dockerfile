# ─────────────────────────────────────────────────────────────────────────────
# Smart Campus Assistant — Frontend Dockerfile (multi-stage)
#
# Stage 1 "builder"  : Node 20 Alpine — installs deps & runs `vite build`
# Stage 2 "serve"    : nginx:alpine   — copies the /dist output & serves it
#
# The final image has NO Node.js, no source code, no node_modules.
# Only the ~2 MB of compiled static assets + a minimal nginx binary.
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# --- Dependency layer (cached unless package*.json changes) ---------------
COPY package.json package-lock.json* ./

# Use --frozen-lockfile to fail loudly if the lock is out of sync.
# Fall back to plain install if no lockfile exists yet.
RUN if [ -f package-lock.json ]; then \
        npm ci --frozen-lockfile; \
    else \
        npm install; \
    fi

# --- Copy application source ----------------------------------------------
COPY index.html      ./
COPY vite.config.js  ./
COPY src/            ./src/

# --- Build-time environment variable -------------------------------------
# VITE_API_URL is baked into the JS bundle at build time by Vite.
# In Docker Compose this is set to "/ask" so Nginx proxies it to the backend.
# Override here or via docker-compose `build.args` / `--build-arg`.
ARG  VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
# --- Production build -----------------------------------------------------
RUN npm run build
# Output lands in /app/dist


# ── Stage 2: Serve ────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS serve

# --- Remove default nginx config ------------------------------------------
RUN rm -f /etc/nginx/conf.d/default.conf

# --- Copy our custom nginx config -----------------------------------------
COPY nginx.conf /etc/nginx/nginx.conf

# --- Copy built assets from Stage 1 --------------------------------------
COPY --from=builder /app/dist /usr/share/nginx/html

# --- Fix permissions so nginx worker (non-root in some distros) can run ──
RUN chmod -R 755 /usr/share/nginx/html && \
    # nginx:alpine already runs as nginx (uid 101) for the worker process.
    # Ensure pid/cache dirs are writable.
    mkdir -p /var/cache/nginx /var/run /tmp && \
    chown -R nginx:nginx /var/cache/nginx /tmp

# --- Expose port ----------------------------------------------------------
EXPOSE 80

# --- Health check ---------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

# --- Start Nginx in foreground (required for Docker) ----------------------
CMD ["nginx", "-g", "daemon off;"]
