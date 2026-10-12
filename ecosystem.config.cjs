module.exports = {
  apps: [
    {
      name: "laptop-backend",
      script: ".venv/bin/python3",
      args: "backend/main.py",
      cwd: __dirname,
      autorestart: true,
      max_restarts: 10,
      env: {
        PORT: "8001",
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "laptop-frontend",
      script: "node_modules/vite/bin/vite.js",
      args: "--host",
      cwd: __dirname,
      autorestart: true,
      max_restarts: 10,
      env: {
        NODE_ENV: "development"
      }
    }
  ]
};
