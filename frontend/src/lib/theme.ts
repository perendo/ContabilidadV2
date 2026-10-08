import { createTheme } from "@mui/material/styles";

const light = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#6750A4" },
    secondary: { main: "#625B71" },
    background: { default: "#FBF8FF", paper: "#FFFBFE" },
  },
  shape: { borderRadius: 12 },
  typography: { fontFamily: "Roboto, 'Segoe UI', sans-serif" },
});

const dark = createTheme({
  palette: {
    mode: "dark",
    primary: { main: "#D0BCFF" },
    secondary: { main: "#CCC2DC" },
    background: { default: "#141218", paper: "#211F26" },
  },
  shape: { borderRadius: 12 },
  typography: { fontFamily: "Roboto, 'Segoe UI', sans-serif" },
});

export function temaSegunModo(modo: "light" | "dark") {
  return modo === "dark" ? dark : light;
}

export default light;