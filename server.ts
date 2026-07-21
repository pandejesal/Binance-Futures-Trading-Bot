import express from "express";
import path from "path";
import fs from "fs";
import { exec } from "child_process";
import { createServer as createViteServer } from "vite";

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json());

  // API Route: Place Order
  app.post("/api/place-order", (req, res) => {
    const { symbol, side, orderType, quantity, price, stopPrice, apiKey, apiSecret } = req.body;

    // Write or update the .env file in both process and trading_bot paths
    const envContent = `BINANCE_API_KEY="${apiKey || ''}"\nBINANCE_API_SECRET="${apiSecret || ''}"\n`;
    try {
      fs.writeFileSync(path.join(process.cwd(), ".env"), envContent);
      fs.writeFileSync(path.join(process.cwd(), "trading_bot", ".env"), envContent);
    } catch (e) {
      console.error("Failed to write env configuration:", e);
    }

    // Build the CLI command using main.py (or setting PYTHONPATH)
    let cmd = `python3 main.py --symbol ${symbol} --side ${side} --type ${orderType} --quantity ${quantity}`;
    if (price) cmd += ` --price ${price}`;
    if (stopPrice) cmd += ` --stop-price ${stopPrice}`;

    // Inject credentials and PYTHONPATH into environment variables
    const processEnv = { 
      ...process.env, 
      PYTHONPATH: `${path.join(process.cwd(), "trading_bot")}:${process.env.PYTHONPATH || ""}`,
      BINANCE_API_KEY: apiKey, 
      BINANCE_API_SECRET: apiSecret 
    };

    exec(cmd, { env: processEnv }, (error, stdout, stderr) => {
      let logContent = "";
      try {
        const logPath = path.join(process.cwd(), "trading_bot.log");
        if (fs.existsSync(logPath)) {
          logContent = fs.readFileSync(logPath, "utf-8");
        }
      } catch (e) {
        logContent = "Failed to load log file.";
      }

      res.json({
        success: error ? false : true,
        stdout,
        stderr,
        logs: logContent,
        error: error ? error.message : null
      });
    });
  });

  // API Route: Run Generic CLI Command
  app.post("/api/run-cli", (req, res) => {
    const { args, apiKey, apiSecret } = req.body;

    const envContent = `BINANCE_API_KEY="${apiKey || ''}"\nBINANCE_API_SECRET="${apiSecret || ''}"\n`;
    try {
      fs.writeFileSync(path.join(process.cwd(), ".env"), envContent);
      fs.writeFileSync(path.join(process.cwd(), "trading_bot", ".env"), envContent);
    } catch (e) {
      console.error("Failed to write env configuration:", e);
    }

    const cmd = `python3 main.py ${args || ''}`;

    const processEnv = { 
      ...process.env, 
      PYTHONPATH: `${path.join(process.cwd(), "trading_bot")}:${process.env.PYTHONPATH || ""}`,
      BINANCE_API_KEY: apiKey, 
      BINANCE_API_SECRET: apiSecret 
    };

    exec(cmd, { env: processEnv }, (error, stdout, stderr) => {
      let logContent = "";
      try {
        const logPath = path.join(process.cwd(), "trading_bot.log");
        if (fs.existsSync(logPath)) {
          logContent = fs.readFileSync(logPath, "utf-8");
        }
      } catch (e) {
        logContent = "Failed to load log file.";
      }

      res.json({
        success: error ? false : true,
        stdout,
        stderr,
        logs: logContent,
        error: error ? error.message : null
      });
    });
  });

  // API Route: Get Logs
  app.get("/api/logs", (req, res) => {
    try {
      const logPath = path.join(process.cwd(), "trading_bot.log");
      if (fs.existsSync(logPath)) {
        res.json({ logs: fs.readFileSync(logPath, "utf-8") });
      } else {
        res.json({ logs: "No logs found. Place an order to generate logs." });
      }
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // API Route: Run Tests
  app.post("/api/run-tests", (req, res) => {
    exec("python3 -m unittest discover -s trading_bot/tests", (error, stdout, stderr) => {
      res.json({
        success: error ? false : true,
        stdout,
        stderr
      });
    });
  });

  // API Route: Clear Logs
  app.post("/api/clear-logs", (req, res) => {
    try {
      const logPath = path.join(process.cwd(), "trading_bot.log");
      if (fs.existsSync(logPath)) {
        fs.unlinkSync(logPath);
      }
      res.json({ success: true });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on port ${PORT}`);
  });
}

startServer();
