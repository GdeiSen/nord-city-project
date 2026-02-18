import type { NextConfig } from "next";
import path from "path";

// Load shared .env from project root (single source of truth for API URL, etc.)
require("dotenv").config({ path: path.resolve(__dirname, "../.env") });
