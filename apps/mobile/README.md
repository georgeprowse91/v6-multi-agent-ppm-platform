# PPM Mobile (Expo)

## Purpose

The PPM Mobile app delivers the core workspace, dashboard, connector, and assistant experiences for iOS and Android using Expo.

The mobile client mirrors the PPM web console experience with a workspace shell, dashboard canvas, connector gallery, and assistant chat. It uses the same API gateway endpoints (`/api/methodologies`, `/api/dashboard`, `/api/connectors`, `/api/assistant`, etc.) and the OIDC login flow exposed at `/login`.

## Prerequisites

- Node.js 18+
- Expo CLI (`npm install --global expo-cli`) or use `npx expo`
- Access to the API gateway (default `http://localhost:8000`)

## Configuration

### Configure the API base URL

Set the API gateway base URL via an Expo public env var:

```bash
export EXPO_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Run locally

```bash
npm install
expo start
```

From the Expo dev tools you can launch iOS, Android, or the web preview. The login screen opens the `/login` OIDC endpoint in your system browser; return to the app to refresh the session after authentication.

## Build for iOS and Android

Use EAS Build or the classic Expo build pipeline:

```bash
npm install -g eas-cli

# iOS
expo prebuild
expo run:ios

# Android
expo prebuild
expo run:android
```

You can also run managed builds using EAS:

```bash
eas build --platform ios
eas build --platform android
```

Refer to the Expo documentation for provisioning profiles and signing setup.

## Ownership and support

- Owner: Platform Engineering
- Support: #ppm-platform-support

