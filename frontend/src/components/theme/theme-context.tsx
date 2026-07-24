"use client";

import { createContext } from "react";

/** Presence marker — true when rendered under ThemeProvider. */
export const ThemeContext = createContext(false);
