# _SlideTap_ front-end

The _SlideTap_ front-end is responsible for serving the user interface for interacting with the _SlideTap_. The front-end communicates with the back-end using REST controllers.

## Requirements

The front-end is written i TypeScript requires Node >= 14. Main dependencies are:

- React
- Material UI
- OpenSeadragon

Vite is used for building and development.

## Structure

- `src\components` contains the React components.
- `src\models` contains the models used in the REST API.
- `src\services` contains services for communication with the REST API.
- `src\index.tsx` is the app entrypoint.

## Development

### Setup

Install the package

```sh
npm install .
```

### Run

Run the development server

```sh
npm run dev
```
