FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
# Empty = same-origin; nginx proxies /auth, /form/*, /responses, /admin/credentials to the API.
ARG VITE_API_BASE_URL=
ARG VITE_FORM_PATH_SLUG=
ARG VITE_ADMIN_PATH_SLUG=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_FORM_PATH_SLUG=$VITE_FORM_PATH_SLUG
ENV VITE_ADMIN_PATH_SLUG=$VITE_ADMIN_PATH_SLUG
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
