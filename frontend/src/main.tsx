import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { App } from "./App";
import { ThemeProvider } from "./providers/ThemeProvider";
import { AuthProvider } from "./providers/AuthProvider";
import { WalletProvider } from "./providers/WalletProvider";
import "./styles/globals.css";

const root = document.getElementById("root");
if (!root) throw new Error("Root element not found");

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <WalletProvider>
          <AuthProvider>
            <App />
            <Toaster
              position="bottom-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: "#111111",
                  color: "#e5e5e5",
                  border: "1px solid #1a1a1a",
                  fontFamily: "SF Mono, monospace",
                  fontSize: "0.875rem",
                },
                success: {
                  iconTheme: {
                    primary: "#14F195",
                    secondary: "#0a0a0a",
                  },
                },
                error: {
                  iconTheme: {
                    primary: "#ef4444",
                    secondary: "#0a0a0a",
                  },
                },
              }}
            />
          </AuthProvider>
        </WalletProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
