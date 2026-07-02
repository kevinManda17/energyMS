import { useColorScheme } from "react-native";
import { themes } from "../theme/colors";
import { useThemeStore } from "../store/theme";

export function useTheme() {
  const systemScheme = useColorScheme();   // OS value: "light" | "dark" | null
  const { theme }    = useThemeStore();    // user choice: "light" | "dark" | "system"

  let effective;
  if (theme === "light")  effective = "light";
  else if (theme === "dark") effective = "dark";
  else effective = systemScheme === "dark" ? "dark" : "light";

  return themes[effective];
}
