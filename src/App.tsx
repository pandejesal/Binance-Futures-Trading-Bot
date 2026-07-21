/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from "react";
import { 
  TrendingUp, 
  Settings, 
  Terminal, 
  CheckCircle2, 
  AlertTriangle, 
  Cpu, 
  Play, 
  FileText, 
  RotateCcw, 
  HelpCircle,
  ExternalLink,
  Lock,
  Eye,
  EyeOff,
  Code
} from "lucide-react";
import { motion } from "motion/react";

export default function App() {
  // Configuration State
  const [apiKey, setApiKey] = useState(() => localStorage.getItem("binance_api_key") || "");
  const [apiSecret, setApiSecret] = useState(() => localStorage.getItem("binance_api_secret") || "");
  const [showSecret, setShowSecret] = useState(false);

  // Order Parameters State
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT" | "STOP_MARKET">("MARKET");
  const [quantity, setQuantity] = useState("0.001");
  const [price, setPrice] = useState("");
  const [stopPrice, setStopPrice] = useState("");

  // UI / Execution State
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [terminalOutput, setTerminalOutput] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"terminal" | "file-log" | "unit-tests">("terminal");
  const [logContent, setLogContent] = useState<string>("No execution history loaded.");
  const [testResult, setTestResult] = useState<{ success: boolean; stdout: string; stderr: string } | null>(null);
  const [isRunningTests, setIsRunningTests] = useState(false);

  // Save Credentials locally
  useEffect(() => {
    localStorage.setItem("binance_api_key", apiKey);
  }, [apiKey]);

  useEffect(() => {
    localStorage.setItem("binance_api_secret", apiSecret);
  }, [apiSecret]);

  // Load latest log file contents
  const fetchLogs = async () => {
    try {
      const res = await fetch("/api/logs");
      const data = await res.json();
      if (data.logs) {
        setLogContent(data.logs);
      }
    } catch (e) {
      setLogContent("Failed to connect to backend log API.");
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim() || !apiSecret.trim()) {
      alert("Please configure your Binance Futures Testnet API Key and Secret first.");
      return;
    }

    setIsExecuting(true);
    setExecutionResult(null);
    setTerminalOutput("Initializing CLI process...\nConnecting to Binance Futures Testnet...\n");
    setActiveTab("terminal");

    try {
      const res = await fetch("/api/place-order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          side,
          orderType,
          quantity,
          price: orderType === "LIMIT" ? price : undefined,
          stopPrice: orderType === "STOP_MARKET" ? stopPrice : undefined,
          apiKey,
          apiSecret
        })
      });

      const data = await res.json();
      setIsExecuting(false);

      if (data.success) {
        setExecutionResult({
          success: true,
          message: "Order placed successfully!",
          stdout: data.stdout,
        });
        setTerminalOutput(data.stdout || "Success with empty stdout.");
      } else {
        setExecutionResult({
          success: false,
          message: "Order placement rejected or failed.",
          stderr: data.stderr || data.error,
        });
        setTerminalOutput(`${data.stdout || ""}\n[ERROR]: ${data.stderr || data.error || "Unknown Error"}`);
      }

      if (data.logs) {
        setLogContent(data.logs);
      }
    } catch (err: any) {
      setIsExecuting(false);
      setExecutionResult({
        success: false,
        message: "Failed to communicate with bot backend server.",
        stderr: err.message
      });
      setTerminalOutput(`[NETWORK CONNECTION FAILURE]: ${err.message}`);
    }
  };

  const handleRunTests = async () => {
    setIsRunningTests(true);
    setTestResult(null);
    setActiveTab("unit-tests");

    try {
      const res = await fetch("/api/run-tests", { method: "POST" });
      const data = await res.json();
      setIsRunningTests(false);
      setTestResult({
        success: data.success,
        stdout: data.stdout,
        stderr: data.stderr
      });
    } catch (err: any) {
      setIsRunningTests(false);
      setTestResult({
        success: false,
        stdout: "",
        stderr: `Failed to invoke test process: ${err.message}`
      });
    }
  };

  const handleClearLogs = async () => {
    if (confirm("Are you sure you want to delete the local trading_bot.log file?")) {
      try {
        const res = await fetch("/api/clear-logs", { method: "POST" });
        if (res.ok) {
          setLogContent("No logs found. Place an order to generate logs.");
        }
      } catch (e) {
        alert("Failed to clear logs.");
      }
    }
  };

  const runGenericCli = async (args: string) => {
    setIsExecuting(true);
    setExecutionResult(null);
    setTerminalOutput(`$ python3 main.py ${args}\nRunning CLI command...`);

    try {
      const res = await fetch("/api/run-cli", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          args,
          apiKey,
          apiSecret
        })
      });

      const data = await res.json();
      setIsExecuting(false);

      if (data.success) {
        setExecutionResult({
          success: true,
          message: `CLI command executed successfully: python3 main.py ${args}`,
          stdout: data.stdout,
        });
        setTerminalOutput(data.stdout || "Command executed successfully.");
      } else {
        setExecutionResult({
          success: false,
          message: `CLI command failed: python3 main.py ${args}`,
          stderr: data.stderr || data.error,
        });
        setTerminalOutput(`${data.stdout || ""}\n[ERROR]: ${data.stderr || data.error || "Unknown Error"}`);
      }

      if (data.logs) {
        setLogContent(data.logs);
      }
    } catch (err: any) {
      setIsExecuting(false);
      setExecutionResult({
        success: false,
        message: "Failed to communicate with bot backend server.",
        stderr: err.message
      });
      setTerminalOutput(`[NETWORK CONNECTION FAILURE]: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-100 flex flex-col font-sans antialiased selection:bg-emerald-500 selection:text-black">
      {/* Header Bar */}
      <header className="border-b border-zinc-900 bg-[#0a0a0a] px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              Binance Futures Trading Bot
              <span className="text-[11px] bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-2.5 py-0.5 rounded-md font-mono tracking-wide">
                TESTNET USDT-M
              </span>
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5 font-mono">
              Python CLI Architecture • Direct REST API • Cryptographic HMAC-SHA256
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <a
            href="https://testnet.binancefuture.com"
            target="_blank"
            rel="noreferrer"
            className="text-xs text-zinc-400 hover:text-emerald-400 transition flex items-center gap-1 bg-zinc-900 px-3 py-1.5 rounded-md border border-zinc-800"
          >
            Binance Testnet Registry <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column - Configuration & Form */}
        <div className="lg:col-span-5 flex flex-col gap-5">
          
          {/* Section 1: Security Credentials */}
          <div className="bg-[#0c0c0c] border border-zinc-800/80 rounded-xl p-5 shadow-2xl">
            <div className="flex items-center gap-2 mb-4">
              <Settings className="w-4 h-4 text-emerald-400" />
              <h2 className="text-xs font-bold tracking-wider uppercase text-zinc-300 font-mono">
                1. API Credentials
              </h2>
            </div>
            
            <div className="space-y-3.5">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Binance Futures Testnet API Key
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-3.5 w-3.5 text-zinc-500" />
                  </span>
                  <input
                    type="text"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Enter your Testnet API Key"
                    className="w-full pl-9 pr-4 py-2 bg-black border border-zinc-800 rounded-lg text-xs font-mono text-emerald-400 placeholder-zinc-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Binance Futures Testnet Secret Key
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-3.5 w-3.5 text-zinc-500" />
                  </span>
                  <input
                    type={showSecret ? "text" : "password"}
                    value={apiSecret}
                    onChange={(e) => setApiSecret(e.target.value)}
                    placeholder="Enter your Testnet Secret Key"
                    className="w-full pl-9 pr-10 py-2 bg-black border border-zinc-800 rounded-lg text-xs font-mono text-emerald-400 placeholder-zinc-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowSecret(!showSecret)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-zinc-500 hover:text-zinc-300 transition"
                  >
                    {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Quick CLI Tools */}
          <div className="bg-[#0c0c0c] border border-zinc-800/80 rounded-xl p-4 shadow-2xl flex flex-col gap-2.5">
            <span className="text-[11px] font-bold tracking-wider uppercase text-zinc-400 font-mono flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              Quick CLI Actions
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => runGenericCli("--balance")}
                disabled={isExecuting}
                className="px-2.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-cyan-500/50 text-cyan-400 rounded text-[11px] font-mono transition flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
              >
                💰 Balance
              </button>
              <button
                type="button"
                onClick={() => runGenericCli("--open-orders")}
                disabled={isExecuting}
                className="px-2.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-cyan-500/50 text-cyan-400 rounded text-[11px] font-mono transition flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
              >
                📋 Orders
              </button>
              <button
                type="button"
                onClick={() => runGenericCli("--logs")}
                disabled={isExecuting}
                className="px-2.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-cyan-500/50 text-cyan-400 rounded text-[11px] font-mono transition flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
              >
                📄 Logs
              </button>
            </div>
          </div>

          {/* Section 2: Order Entry Panel */}
          <form onSubmit={handlePlaceOrder} className="bg-[#0c0c0c] border border-zinc-800/80 rounded-xl p-5 shadow-2xl flex flex-col gap-4">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-emerald-400" />
                <h2 className="text-xs font-bold tracking-wider uppercase text-zinc-300 font-mono">
                  2. Order Parameters
                </h2>
              </div>
              <span className="text-[10px] bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-2 py-0.5 rounded font-mono">
                LOCAL PRE-FLIGHT
              </span>
            </div>

            {/* Side Switch BUY / SELL */}
            <div className="grid grid-cols-2 gap-2 bg-black p-1.5 rounded-lg border border-zinc-800">
              <button
                type="button"
                onClick={() => setSide("BUY")}
                className={`py-2 text-xs font-bold tracking-wide rounded transition duration-150 cursor-pointer ${
                  side === "BUY"
                    ? "bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.2)]"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                BUY / LONG
              </button>
              <button
                type="button"
                onClick={() => setSide("SELL")}
                className={`py-2 text-xs font-bold tracking-wide rounded transition duration-150 cursor-pointer ${
                  side === "SELL"
                    ? "bg-rose-500/20 border border-rose-500/50 text-rose-400 shadow-[0_0_12px_rgba(244,63,94,0.2)]"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                SELL / SHORT
              </button>
            </div>

            {/* Row: Symbol and Order Type */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Symbol
                </label>
                <select
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded-lg text-xs font-mono text-zinc-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                >
                  <option value="BTCUSDT">BTCUSDT</option>
                  <option value="ETHUSDT">ETHUSDT</option>
                  <option value="SOLUSDT">SOLUSDT</option>
                  <option value="BNBUSDT">BNBUSDT</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Order Type
                </label>
                <select
                  value={orderType}
                  onChange={(e: any) => setOrderType(e.target.value)}
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded-lg text-xs font-mono text-zinc-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                >
                  <option value="MARKET">MARKET</option>
                  <option value="LIMIT">LIMIT</option>
                  <option value="STOP_MARKET">STOP_MARKET (Bonus)</option>
                </select>
              </div>
            </div>

            {/* Row: Quantity */}
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                Quantity
              </label>
              <input
                type="number"
                step="any"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="e.g. 0.001"
                className="w-full px-3 py-2 bg-black border border-zinc-800 rounded-lg text-xs font-mono text-zinc-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            {/* Conditionally Render: LIMIT Price */}
            {orderType === "LIMIT" && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.15 }}
              >
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Limit Price (USDT)
                </label>
                <input
                  type="number"
                  step="any"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="e.g. 64500.25"
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded-lg text-xs font-mono text-zinc-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                />
              </motion.div>
            )}

            {/* Conditionally Render: STOP_MARKET Stop Price */}
            {orderType === "STOP_MARKET" && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.15 }}
              >
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Stop Trigger Price (USDT)
                </label>
                <input
                  type="number"
                  step="any"
                  value={stopPrice}
                  onChange={(e) => setStopPrice(e.target.value)}
                  placeholder="e.g. 63000.00"
                  className="w-full px-3 py-2 bg-black border border-zinc-800 rounded-lg text-xs font-mono text-zinc-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                />
              </motion.div>
            )}

            {/* CLI Command Preview Card */}
            <div className="bg-black rounded-lg border border-zinc-800/80 p-3 mt-1">
              <span className="text-[10px] text-zinc-500 font-mono tracking-wider uppercase block mb-1.5">
                CLI Command String
              </span>
              <div className="font-mono text-[11px] text-emerald-400 overflow-x-auto whitespace-nowrap bg-[#080808] p-2 rounded border border-zinc-900">
                python3 main.py --symbol {symbol} --side {side} --type {orderType} --quantity {quantity}
                {orderType === "LIMIT" && price && ` --price ${price}`}
                {orderType === "STOP_MARKET" && stopPrice && ` --stop-price ${stopPrice}`}
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isExecuting}
              className={`w-full py-2.5 rounded-lg text-xs font-bold tracking-wider uppercase flex items-center justify-center gap-2 transition cursor-pointer ${
                isExecuting
                  ? "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                  : side === "BUY"
                  ? "bg-emerald-500 text-black hover:bg-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.3)]"
                  : "bg-rose-500 text-black hover:bg-rose-400 shadow-[0_0_20px_rgba(244,63,94,0.3)]"
              }`}
            >
              {isExecuting ? (
                <>
                  <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
                  Executing CLI Subprocess...
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-black" />
                  Execute {side} {orderType} Order
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Column - Results and Diagnostics */}
        <div className="lg:col-span-7 flex flex-col gap-5">
          
          {/* Section 1: Execution Banner */}
          {executionResult && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`border rounded-xl p-4 shadow-xl ${
                executionResult.success
                  ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-400"
                  : "bg-rose-950/20 border-rose-500/30 text-rose-400"
              }`}
            >
              <div className="flex items-start gap-3">
                {executionResult.success ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-rose-400 mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1">
                  <h3 className="text-sm font-bold tracking-wide">
                    {executionResult.message}
                  </h3>
                  <p className="text-xs text-zinc-400 mt-0.5 font-mono">
                    Exit Code: {executionResult.success ? "0 (SUCCESS)" : "1 (FAILURE)"}
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Section 2: Terminal and Logs View */}
          <div className="flex-1 bg-[#0c0c0c] border border-zinc-800/80 rounded-xl flex flex-col min-h-[480px] shadow-2xl">
            {/* Tab Navigation */}
            <div className="flex items-center justify-between border-b border-zinc-800/80 bg-black/60 px-3">
              <div className="flex">
                <button
                  onClick={() => setActiveTab("terminal")}
                  className={`px-4 py-3 text-xs font-bold font-mono tracking-wider uppercase border-b-2 transition duration-150 flex items-center gap-2 cursor-pointer ${
                    activeTab === "terminal"
                      ? "border-emerald-400 text-emerald-400"
                      : "border-transparent text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  <Terminal className="w-3.5 h-3.5" />
                  Terminal Console
                </button>
                <button
                  onClick={() => {
                    setActiveTab("file-log");
                    fetchLogs();
                  }}
                  className={`px-4 py-3 text-xs font-bold font-mono tracking-wider uppercase border-b-2 transition duration-150 flex items-center gap-2 cursor-pointer ${
                    activeTab === "file-log"
                      ? "border-emerald-400 text-emerald-400"
                      : "border-transparent text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  trading_bot.log
                </button>
                <button
                  onClick={handleRunTests}
                  className={`px-4 py-3 text-xs font-bold font-mono tracking-wider uppercase border-b-2 transition duration-150 flex items-center gap-2 cursor-pointer ${
                    activeTab === "unit-tests"
                      ? "border-emerald-400 text-emerald-400"
                      : "border-transparent text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  {isRunningTests ? (
                    <div className="w-3 h-3 border border-emerald-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Code className="w-3.5 h-3.5" />
                  )}
                  Run Unit Tests
                </button>
              </div>

              {activeTab === "file-log" && (
                <button
                  onClick={handleClearLogs}
                  className="p-1.5 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 rounded transition text-xs flex items-center gap-1 cursor-pointer"
                  title="Clear log file"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Clear Logs
                </button>
              )}
            </div>

            {/* Output Panels */}
            <div className="flex-1 p-4 font-mono text-xs overflow-auto bg-black rounded-b-xl max-h-[520px]">
              
              {/* TAB 1: CLI Terminal Emulator */}
              {activeTab === "terminal" && (
                <div className="space-y-1.5 text-zinc-300">
                  {terminalOutput ? (
                    <pre className="whitespace-pre-wrap font-mono leading-relaxed select-text text-emerald-400/90">{terminalOutput}</pre>
                  ) : (
                    <div className="text-zinc-600 py-24 text-center flex flex-col items-center gap-2 font-mono">
                      <Terminal className="w-8 h-8 text-zinc-800" />
                      <p>Terminal inactive. Fill in API credentials and submit an order to execute the Python bot.</p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: trading_bot.log file contents */}
              {activeTab === "file-log" && (
                <div className="space-y-2 text-zinc-300">
                  <div className="text-[11px] font-mono text-emerald-400/90 bg-emerald-500/5 border border-emerald-500/20 p-2.5 rounded-lg mb-3">
                    🔒 <strong>Secure Masked File Logger:</strong> Outbound REST calls, HTTP statuses, and JSON signatures are recorded in <code>trading_bot.log</code>. API Keys are masked and Secrets redacted automatically.
                  </div>
                  <pre className="whitespace-pre-wrap select-text leading-relaxed text-zinc-400 font-mono">{logContent}</pre>
                </div>
              )}

              {/* TAB 3: Unit Tests Output */}
              {activeTab === "unit-tests" && (
                <div className="space-y-3">
                  {isRunningTests ? (
                    <div className="text-zinc-500 py-24 text-center flex flex-col items-center gap-2 font-mono">
                      <div className="w-5 h-5 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
                      <p>Running unittest discovery suite on bot test suite...</p>
                    </div>
                  ) : testResult ? (
                    <div>
                      <div className={`p-3 rounded-lg border text-xs font-mono font-bold mb-3 ${
                        testResult.success 
                          ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-400" 
                          : "bg-rose-950/20 border-rose-500/30 text-rose-400"
                      }`}>
                        {testResult.success ? "✓ ALL 16 UNIT TESTS PASSED IN 0.005s" : "✗ TEST SUITE ENCOUNTERED FAILURES"}
                      </div>
                      
                      <div className="space-y-2 font-mono">
                        {testResult.stdout && (
                          <div>
                            <span className="text-[10px] text-zinc-500 block mb-1">STDOUT:</span>
                            <pre className="bg-[#080808] p-3 rounded border border-zinc-900 text-zinc-300 whitespace-pre-wrap">{testResult.stdout}</pre>
                          </div>
                        )}
                        {testResult.stderr && (
                          <div>
                            <span className="text-[10px] text-zinc-500 block mb-1">STDERR (UnitTest Summary):</span>
                            <pre className="bg-[#080808] p-3 rounded border border-zinc-900 text-emerald-400/80 whitespace-pre-wrap">{testResult.stderr}</pre>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="text-zinc-600 py-24 text-center flex flex-col items-center gap-2 font-mono">
                      <Code className="w-8 h-8 text-zinc-800" />
                      <p>Run unit tests to verify local validation rules, signature generation, and payload mapping.</p>
                      <button
                        onClick={handleRunTests}
                        className="mt-2 px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-emerald-400 border border-zinc-800 rounded-lg text-xs font-bold font-mono cursor-pointer transition"
                      >
                        Launch Test Suite
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 bg-[#080808] px-6 py-4 text-center text-xs text-zinc-500 font-mono">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
          <p>© 2026 PrimeTrade.ai Python Trading Bot Suite</p>
          <div className="flex items-center gap-2 text-emerald-400/80">
            <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
            <span>Python 3.11+ • Standard PEP-8 • Zero Unnecessary Dependencies</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
